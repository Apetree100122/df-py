#taken from https://cryptomarketpool.com/use-the-graph-to-query-ethereum-data-in-python/

import requests
# pretty print is used to print the output in the console in an easy to read format
from pprint import pprint


# function to use requests.post to make an API call to the subgraph url
def run_query(q):

    # endpoint where you are making the request
    request = requests.post('https://api.thegraph.com/subgraphs/name/oceanprotocol/ocean-subgraph/'
                            '',
                            json={'query': query})
    if request.status_code == 200:
        return request.json()
    else:
        raise Exception('Query failed. return code is {}.      {}'.format(request.status_code, query))


# The Graph query - Query Uniswap for a list of the top 10 pairs where the reserve is > 1000000 USD and the volume is >50000 USD
query = """
{
  datatokens(orderBy: createTime, orderDirection: desc) {
    address
    symbol
    name
    cap
    supply
    publisher
    holderCount
  }
}
"""
result = run_query(query)

# print the results
print('Print Result - {}'.format(result))
print('#############')
# pretty print the results
pprint(result)

