from unittest.mock import patch

import pytest
from enforce_typing import enforce_types

from df_py.util import dispense, networkutil, oceantestutil, oceanutil
from df_py.util.base18 import from_wei, to_wei
from df_py.util.contract_base import ContractBase

all_accounts = oceantestutil.get_all_accounts()
accounts = all_accounts

a1 = accounts[1]
a2 = accounts[2]
a3 = accounts[3]


@enforce_types
def test_small_batch(w3):
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    df_strategy = ContractBase(
        w3, "DFStrategyV1", constructor_args=[df_rewards.address]
    )

    rewards_at_chain = {a1.address: 0.1, a2.address: 0.2, a3.address: 0.3}
    dispense.dispense(
        w3,
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=OCEAN.address,
        from_account=accounts[0],
    )

    # a1 claims for itself
    bal_before = from_wei(OCEAN.balanceOf(a1))
    df_strategy.claim([OCEAN.address], {"from": accounts[1]})
    bal_after = from_wei(OCEAN.balanceOf(a1))
    assert (bal_after - bal_before) == pytest.approx(0.1)

    # a8 claims on behalf of a1
    bal_before = from_wei(OCEAN.balanceOf(a3))
    df_rewards.claimFor(a3, OCEAN.address, {"from": accounts[8]})
    bal_after = from_wei(OCEAN.balanceOf(a3))
    assert (bal_after - bal_before) == pytest.approx(0.3)


@enforce_types
def test_batching(w3):
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])

    batch_size = 2
    total_number = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= total_number

    rewards_at_chain = {accounts[i].address: (i + 1.0) for i in range(total_number)}

    dispense.dispense(
        w3,
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=OCEAN.address,
        from_account=accounts[0],
        batch_size=batch_size,
    )

    for i in range(total_number):
        assert df_rewards.claimable(accounts[i], OCEAN.address) > 0


@enforce_types
def test_batch_number(w3):
    token = ContractBase(
        w3, "OceanToken", constructor_args=["TOK", "TOK", 18, to_wei(100e18)]
    )

    df_rewards = ContractBase(w3, "DFRewards", constructor_args=[])
    batch_size = 2
    total_number = batch_size * 3 + 1  # enough accounts to ensure batching
    assert len(accounts) >= total_number

    rewards_at_chain = {accounts[i].address: (i + 1.0) for i in range(total_number)}

    dispense.dispense(
        w3,
        rewards_at_chain,
        dfrewards_addr=df_rewards.address,
        token_addr=token.address,
        from_account=accounts[0],
        batch_size=batch_size,
        batch_number=2,
    )

    assert df_rewards.claimable(accounts[batch_size - 1], token.address) == 0
    assert df_rewards.claimable(accounts[batch_size], token.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 1], token.address) > 0
    assert df_rewards.claimable(accounts[batch_size + 2], token.address) == 0


def test_dispense_passive(w3):
    fee_distributor = oceanutil.FeeDistributor(networkutil.DEV_CHAINID)
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    with patch("df_py.util.dispense.chain_id_to_multisig_addr"):
        with patch("df_py.util.dispense.send_multisig_tx") as mock:
            dispense.dispense_passive(w3, OCEAN, fee_distributor, 1)

    assert mock.call_count == 3


def test_multisig_transfer_tokens(w3):
    OCEAN = oceanutil.OCEAN_token(networkutil.DEV_CHAINID)
    with patch("df_py.util.dispense.chain_id_to_multisig_addr"):
        with patch("df_py.util.dispense.send_multisig_tx") as mock:
            dispense.multisig_transfer_tokens(w3, OCEAN, OCEAN.address, 1)
    assert mock.call_count == 1


@enforce_types
def setup_function():
    oceantestutil.fill_accounts_with_OCEAN(accounts)
