import os

# pylint: disable=logging-fstring-interpolation
from typing import Dict, Optional, Union

from enforce_typing import enforce_types
from web3.main import Web3

from df_py.util.base18 import to_wei
from df_py.util.contract_base import ContractBase
from df_py.util.logger import logger
from df_py.util.multisig import send_multisig_tx
from df_py.util.networkutil import chain_id_to_multisig_addr

MAX_BATCH_SIZE = 500
TRY_AGAIN = 3


# pylint: disable=too-many-statements
@enforce_types
def dispense(
    web3: Web3,
    rewards: Dict[str, float],
    dfrewards_addr: str,
    token_addr: str,
    from_account,
    batch_size: int = MAX_BATCH_SIZE,
    batch_number: Optional[int] = None,
):
    """
    @description
      Allocate rewards to LPs.

    @arguments
      rewards -- dict of [LP_addr]:TOKEN_amt (float, not wei)
        -- rewards for each LP
      dfrewards_addr -- address of dfrewards contract
      token_addr -- address of token we're allocating rewards with (eg OCEAN)
      from_account -- account doing the spending
      batch_size -- largest # LPs allocated per tx (due to EVM limits)
      batch_number -- specify the batch number to run dispense only for that batch.

    @return
      <<nothing, but updates the dfrewards contract on-chain>>
    """
    logger.info("dispense: begin")
    logger.info(f"  # addresses: {len(rewards)}")
    multisigaddr = None
    usemultisig = os.getenv("USE_MULTISIG", "false") == "true"
    if usemultisig:
        logger.info("multisig enabled")
        multisigaddr = chain_id_to_multisig_addr(web3.eth.chain_id)
    df_rewards = ContractBase(web3, "DFRewards", dfrewards_addr)
    TOK = ContractBase(web3, "OceanToken", token_addr)
    logger.info(f"  Total amount: {sum(rewards.values())} {TOK.symbol()}")

    # checksum addresses
    rewards = {web3.to_checksum_address(k): v for k, v in rewards.items()}
    to_addrs = list(rewards.keys())
    values = [to_wei(rewards[to_addr]) for to_addr in to_addrs]

    N = len(rewards)
    sts = list(range(N))[::batch_size]  # send in batches to avoid gas issues

    LEGACY_TX = False
    if web3.eth.chain_id == 23294:
        LEGACY_TX = True

    def approveAmt(amt):
        if usemultisig:
            data = TOK.contract.encodeABI(
                fn_name="approve", args=[df_rewards.address, amt]
            )
            value = 0
            to = TOK.address
            # data = bytes.fromhex(data[2:])
            send_multisig_tx(multisigaddr, web3, to, value, data)
            return
        tx_dict = {
            "from": from_account,
        }
        if LEGACY_TX:
            # gas price: legacy tx for Sapphire
            tx_dict["gasPrice"] = web3.eth.gas_price
        TOK.approve(df_rewards, amt, tx_dict)

    if batch_number is not None:
        b_st = (batch_number - 1) * batch_size
        approveAmt(sum(values[b_st : b_st + batch_size]))
    else:
        approveAmt(sum(values))

    logger.info(f"Total {len(sts)} batches")
    for i, st in enumerate(sts):
        if batch_number is not None and batch_number != i + 1:
            continue
        fin = st + batch_size
        done = False
        for z in range(TRY_AGAIN):
            # pylint: disable=line-too-long
            logger.info(
                f"Allocating rewards Batch #{(i+1)}/{len(sts)}, {len(to_addrs[st:fin])} addresses {z}"
            )

            # if env use multisig
            if usemultisig:
                # get data of tx
                data = df_rewards.contract.encodeABI(
                    fn_name="allocate",
                    args=[to_addrs[st:fin], values[st:fin], TOK.address],
                )
                # value is 0
                value = 0
                to = df_rewards.address
                # convert data to bytes
                # data = bytes.fromhex(data[2:])

                send_multisig_tx(multisigaddr, web3, to, value, data)
            else:
                tx_dict = {
                    "from": from_account,
                }
                if LEGACY_TX:
                    # gas price: legacy tx for Sapphire
                    tx_dict["gasPrice"] = web3.eth.gas_price
                df_rewards.allocate(
                    to_addrs[st:fin],
                    values[st:fin],
                    TOK.address,
                    tx_dict,  # gas price: legacy tx for Sapphire
                )
            done = True
            break

        if done is False:
            logger.critical(f"Could not allocate funds for batch {i+1}")
    logger.info("dispense: done")


@enforce_types
def dispense_passive(web3, ocean, feedistributor, amount: Union[float, int]):
    amount_wei = to_wei(amount)
    transfer_data = ocean.contract.encodeABI(
        fn_name="transfer", args=[feedistributor.address, amount_wei]
    )

    checkpoint_total_supply_data = feedistributor.contract.encodeABI(
        fn_name="checkpoint_total_supply"
    )
    checkpoint_token_data = feedistributor.contract.encodeABI(
        fn_name="checkpoint_token"
    )

    multisig_addr = chain_id_to_multisig_addr(web3.eth.chain_id)
    send_multisig_tx(multisig_addr, web3, ocean.address, 0, transfer_data)

    for data in [checkpoint_total_supply_data, checkpoint_token_data]:
        send_multisig_tx(multisig_addr, web3, feedistributor.address, 0, data)


@enforce_types
def multisig_transfer_tokens(web3, ocean, receiver_address, amount):
    amount_wei = to_wei(amount)
    transfer_data = ocean.contract.encodeABI(
        fn_name="transfer", args=[receiver_address, amount_wei]
    )

    multisig_addr = chain_id_to_multisig_addr(web3.eth.chain_id)
    send_multisig_tx(multisig_addr, web3, ocean.address, 0, transfer_data)
