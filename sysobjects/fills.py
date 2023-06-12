import datetime
from dataclasses import dataclass

import pandas as pd

from sysexecution.orders.named_order_objects import missing_order, not_filled

from sysexecution.orders.base_orders import Order


@dataclass
class Fill:
    date: datetime.datetime
    qty: int
    price: float
    price_requires_slippage_adjustment: bool = False


class ListOfFills(list):
    def __init__(self, list_of_fills):
        list_of_fills = [
            fill for fill in list_of_fills if fill is not (missing_order or not_filled)
        ]
        super().__init__(list_of_fills)

    def _as_dict_of_lists(self) -> dict:
        qty_list = [fill.qty for fill in self]
        price_list = [fill.price for fill in self]
        date_list = [fill.date for fill in self]

        return dict(qty=qty_list, price=price_list, date=date_list)

    def as_pd_df(self) -> pd.DataFrame:
        self_as_dict = self._as_dict_of_lists()
        date_index = self_as_dict.pop("date")
        df = pd.DataFrame(self_as_dict, index=date_index)
        df = df.sort_index()

        return df

    @classmethod
    def from_position_series_and_prices(cls, positions: pd.Series, price: pd.Series):

        list_of_fills = _list_of_fills_from_position_series_and_prices(
            positions=positions, price=price
        )

        return cls(list_of_fills)


def _list_of_fills_from_position_series_and_prices(
    positions: pd.Series, price: pd.Series
) -> ListOfFills:

    (
        trades_without_zeros,
        prices_aligned_to_trades,
    ) = _get_valid_trades_and_aligned_prices(positions=positions, price=price)

    trades_as_list = list(trades_without_zeros.values)
    prices_as_list = list(prices_aligned_to_trades.values)
    dates_as_list = list(prices_aligned_to_trades.index)

    list_of_fills_as_list = [
        Fill(date, qty, price)
        for date, qty, price in zip(dates_as_list, trades_as_list, prices_as_list)
    ]

    list_of_fills = ListOfFills(list_of_fills_as_list)

    return list_of_fills


def _get_valid_trades_and_aligned_prices(
    positions: pd.Series, price: pd.Series
) -> tuple:
    # No delaying done here so we assume positions are already delayed
    trades = positions.diff()
    trades_without_na = trades[~trades.isna()]
    trades_without_zeros = trades_without_na[trades_without_na != 0]

    prices_aligned_to_trades = price.reindex(trades_without_zeros.index, method="ffill")

    return trades_without_zeros, prices_aligned_to_trades


def fill_from_order(order: Order) -> Fill:
    try:
        assert len(order.trade) == 1
    except:
        raise Exception("Can't get fills from multi-leg orders")

    if order.fill_equals_zero():
        return missing_order

    fill_price = order.filled_price
    fill_datetime = order.fill_datetime
    fill_qty = order.fill[0]

    if fill_price is None:
        return missing_order

    if fill_datetime is None:
        return missing_order

    return Fill(fill_datetime, fill_qty, fill_price)
