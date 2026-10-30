import aiohttp
import base64
import struct
from typing import Any

DEX_TOKEN_PAIRS = "https://api.dexscreener.com/token-pairs/v1/solana/{}"

class DataProvider:
    def __init__(self, rpc_url: str):
        self.rpc_url = rpc_url
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def _json(self, url: str, *, method="GET", payload=None):
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            async with session.request(method, url, json=payload) as response:
                response.raise_for_status()
                return await response.json()

    async def market_data(self, address: str) -> dict[str, Any]:
        data = await self._json(DEX_TOKEN_PAIRS.format(address))
        if not isinstance(data, list) or not data:
            raise ValueError("No DexScreener Solana pair data found for that address.")
        # Use the most liquid pair to reduce misleading results from dust pools.
        pairs = [p for p in data if p.get("chainId") == "solana"]
        if not pairs:
            raise ValueError("No Solana trading pair found for this token.")
        pairs.sort(key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0), reverse=True)
        return pairs[0]

    async def rpc(self, method: str, params: list):
        payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        result = await self._json(self.rpc_url, method="POST", payload=payload)
        if "error" in result:
            raise RuntimeError(str(result["error"]))
        return result.get("result")

    async def mint_checks(self, address: str) -> dict[str, Any]:
        """Read SPL mint authority/freeze authority and top token accounts using public RPC."""
        info = await self.rpc("getAccountInfo", [address, {"encoding": "base64", "commitment": "confirmed"}])
        value = (info or {}).get("value")
        if not value:
            raise ValueError("Mint account not found on the configured Solana RPC.")
        encoded = value["data"][0]
        raw = base64.b64decode(encoded)
        if len(raw) < 82:
            raise ValueError("Account data is too short to be a standard SPL mint.")
        mint_tag = struct.unpack_from("<I", raw, 0)[0]
        supply_raw = struct.unpack_from("<Q", raw, 36)[0]
        decimals = raw[44]
        freeze_tag = struct.unpack_from("<I", raw, 46)[0]
        mint_authority = mint_tag == 1
        freeze_authority = freeze_tag == 1
        supply = supply_raw / (10 ** decimals) if decimals >= 0 else float(supply_raw)

        largest = await self.rpc("getTokenLargestAccounts", [address, {"commitment": "confirmed"}])
        accounts = (largest or {}).get("value", [])
        top_amounts = []
        for item in accounts:
            try:
                top_amounts.append(float(item.get("uiAmount") or 0))
            except (TypeError, ValueError):
                pass
        top10_share = (sum(top_amounts) / supply * 100) if supply > 0 else None
        largest_share = (max(top_amounts) / supply * 100) if supply > 0 and top_amounts else None
        return {
            "mint_authority_enabled": mint_authority,
            "freeze_authority_enabled": freeze_authority,
            "supply": supply,
            "decimals": decimals,
            "top10_account_share_pct": top10_share,
            "largest_account_share_pct": largest_share,
            "token_program": value.get("owner"),
        }
