import asyncio

from ezib_async import ezIBAsync

async def main():

    ezib = ezIBAsync()
    await ezib.connectAsync(ibhost='localhost', ibport=4001, ibclient=100)

    # unnecessary for single-account
    ezib.requestAccountUpdates(subscribe=True)
    await asyncio.sleep(2)

    print("\nAccount Information")
    print(ezib.account)

    print("\nPositions")
    print(ezib.positions)

    print("\nPortfolio")
    print(ezib.portfolio)

    print("\nContracts")
    print(ezib.contracts)

    ezib.requestAccountUpdates(subscribe=False)

if __name__ == "__main__":
    asyncio.run(main())