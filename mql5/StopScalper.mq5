//+------------------------------------------------------------------+
//| StopScalper.mq5                                                  |
//| Buy stop and sell stop near the price. One fill cancels the     |
//| other. Safety stop, auto break-even, trailing. On close, one    |
//| reversal, then the next M1 bar places a fresh pair.             |
//|                                                                  |
//| Paste this file into MQL5/Experts and compile. Attach it to any |
//| chart. Orders refresh on each new M1 bar, at Ask/Bid ± entry.   |
//|                                                                  |
//| Points match the Strateg tester:                                |
//|   gold / bitcoin  1 point = 0.01                                 |
//|   JPY pairs       1 point = 0.001                                |
//|   other FX        1 point = 0.00001  (0.1 pip)                   |
//|                                                                  |
//| Use a hedging account, or run this EA alone on the symbol.      |
//| A reversal does not reverse again.                               |
//+------------------------------------------------------------------+
#property copyright "Strateg"
#property version   "1.00"
#property description "OCO buy/sell stops, safety SL, auto BE, trail, one reversal."

#include <Trade/Trade.mqh>

input group "Stops"
input double InpEntryPts    = 50.0;    // Entry distance (points)
input double InpSlPts       = 500.0;   // Safety SL (points)
input double InpTrailPts    = 100.0;   // Trailing stop (points, 0 = off)
input double InpTrailArmPts = 200.0;   // Trailing arm (points, 0 = arm at the trail distance)
input double InpBePts       = 0.0;     // Auto BE (points, 0 = off)
input bool   InpHourFilter  = false;   // Skip weak server hours
input int    InpSkipMask    = 12625184;// Skip hours 5, 8, 10, 13, 15, 22, 23

input group "Trade"
input bool   InpReverse     = true;    // Reverse once after the stop entry closes
input double InpLots        = 0.01;    // Lot size
input ulong  InpMagic       = 20261006;// Magic number
input int    InpSlippagePts = 30;      // Max slippage (points)

CTrade trade;

#define ORIGIN_NONE  0
#define ORIGIN_STOP  1
#define ORIGIN_REV   2

int      g_origin       = ORIGIN_NONE;
int      g_dir          = 0;
double   g_best         = 0.0;
bool     g_in_position  = false;
bool     g_need_reverse = false;
bool     g_expect_rev   = false;
int      g_reverse_dir  = 0;
datetime g_reverse_bar  = 0;
datetime g_wait_bar     = 0;
datetime g_placed_bar   = 0;
double   g_last_sl_try  = 0.0;
string   g_last_error   = "";

double StrategPoint()
{
   string s = _Symbol;
   StringToUpper(s);
   if(StringFind(s, "XAU") >= 0 || StringFind(s, "GOLD") >= 0 || StringFind(s, "BTC") >= 0)
      return 0.01;
   if(StringFind(s, "JPY") >= 0)
      return 0.001;
   return 0.00001;
}

double Px(const double pts)
{
   return pts * StrategPoint();
}

bool HourAllowed()
{
   if(!InpHourFilter)
      return true;
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.hour < 0 || dt.hour > 23)
      return true;
   return (InpSkipMask & (1 << dt.hour)) == 0;
}

bool MarketOpen()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   const int now = dt.hour * 3600 + dt.min * 60 + dt.sec;
   datetime from = 0, to = 0;
   bool any = false;
   for(uint i = 0; i < 8; ++i)
   {
      if(!SymbolInfoSessionTrade(_Symbol, (ENUM_DAY_OF_WEEK)dt.day_of_week, i, from, to))
         break;
      any = true;
      if(now >= (int)from && now < (int)to)
         return true;
   }
   return !any;
}

double MinDist()
{
   const int stops = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_STOPS_LEVEL);
   const int freeze = (int)SymbolInfoInteger(_Symbol, SYMBOL_TRADE_FREEZE_LEVEL);
   double dist = MathMax(stops, freeze) * _Point;
   if(dist < _Point)
      dist = _Point;
   return dist;
}

double NormLots(double lots)
{
   const double step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   const double minv = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   const double maxv = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   const double use = (step > 0.0 ? step : 0.01);
   lots = MathFloor(lots / use + 1e-8) * use;
   if(lots < minv)
      lots = minv;
   if(maxv > 0.0 && lots > maxv)
      lots = maxv;
   return NormalizeDouble(lots, 8);
}

int BrokerPoints(const double pts)
{
   if(_Point <= 0.0)
      return 0;
   return (int)MathRound(Px(pts) / _Point);
}

bool Tighter(const bool buy, const double candidate, const double current)
{
   if(candidate <= 0.0)
      return false;
   if(current <= 0.0)
      return true;
   if(buy)
      return candidate > current + _Point * 0.5;
   return candidate < current - _Point * 0.5;
}

void Note(const string text)
{
   if(text == g_last_error)
      return;
   g_last_error = text;
   if(StringLen(text) > 0)
      Print("StopScalper: ", text);
}

bool SelectOurs()
{
   for(int i = PositionsTotal() - 1; i >= 0; --i)
   {
      const ulong ticket = PositionGetTicket(i);
      if(ticket == 0)
         continue;
      if(PositionGetString(POSITION_SYMBOL) != _Symbol)
         continue;
      if((ulong)PositionGetInteger(POSITION_MAGIC) != InpMagic)
         continue;
      return true;
   }
   return false;
}

void DeletePending()
{
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      const ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;
      const ENUM_ORDER_TYPE kind = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(kind != ORDER_TYPE_BUY_STOP && kind != ORDER_TYPE_SELL_STOP)
         continue;
      if(!trade.OrderDelete(ticket))
         Note("delete pending failed: " + trade.ResultRetcodeDescription());
   }
}

int PendingCount(int &buys, int &sells)
{
   buys = 0;
   sells = 0;
   for(int i = OrdersTotal() - 1; i >= 0; --i)
   {
      const ulong ticket = OrderGetTicket(i);
      if(ticket == 0)
         continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol)
         continue;
      if((ulong)OrderGetInteger(ORDER_MAGIC) != InpMagic)
         continue;
      const ENUM_ORDER_TYPE kind = (ENUM_ORDER_TYPE)OrderGetInteger(ORDER_TYPE);
      if(kind == ORDER_TYPE_BUY_STOP)
         ++buys;
      else if(kind == ORDER_TYPE_SELL_STOP)
         ++sells;
   }
   return buys + sells;
}

bool PlaceStops()
{
   const double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   const double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
      return false;

   const double min_dist = MinDist();
   double entry = Px(InpEntryPts);
   if(entry < min_dist)
      entry = min_dist;
   double sl_dist = Px(InpSlPts);
   if(sl_dist < min_dist)
      sl_dist = min_dist;

   const double lots = NormLots(InpLots);
   const double buy_px = NormalizeDouble(ask + entry, _Digits);
   const double sell_px = NormalizeDouble(bid - entry, _Digits);
   const double buy_sl = NormalizeDouble(buy_px - sl_dist, _Digits);
   const double sell_sl = NormalizeDouble(sell_px + sl_dist, _Digits);

   int buys = 0, sells = 0;
   PendingCount(buys, sells);
   bool ok = true;
   if(buys < 1)
   {
      if(!trade.BuyStop(lots, buy_px, _Symbol, buy_sl, 0.0, ORDER_TIME_GTC, 0, "stop"))
      {
         Note("buy stop failed: " + trade.ResultRetcodeDescription());
         ok = false;
      }
   }
   if(sells < 1)
   {
      if(!trade.SellStop(lots, sell_px, _Symbol, sell_sl, 0.0, ORDER_TIME_GTC, 0, "stop"))
      {
         Note("sell stop failed: " + trade.ResultRetcodeDescription());
         ok = false;
      }
   }
   if(ok)
      Note("");
   return ok;
}

void SendReverse()
{
   if(!MarketOpen() || !HourAllowed())
      return;
   const double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   const double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   if(ask <= 0.0 || bid <= 0.0)
      return;
   const double min_dist = MinDist();
   double sl_dist = Px(InpSlPts);
   if(sl_dist < min_dist)
      sl_dist = min_dist;
   const double lots = NormLots(InpLots);
   bool sent = false;
   if(g_reverse_dir > 0)
   {
      const double sl = NormalizeDouble(ask - sl_dist, _Digits);
      sent = trade.Buy(lots, _Symbol, ask, sl, 0.0, "reverse");
   }
   else if(g_reverse_dir < 0)
   {
      const double sl = NormalizeDouble(bid + sl_dist, _Digits);
      sent = trade.Sell(lots, _Symbol, bid, sl, 0.0, "reverse");
   }
   if(!sent)
   {
      g_expect_rev = false;
      Note("reverse failed: " + trade.ResultRetcodeDescription());
      return;
   }
   g_need_reverse = false;
   g_expect_rev = true;
   Note("");
   if(SelectOurs())
      RememberPosition();
}

void RememberPosition()
{
   const bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
   g_dir = buy ? 1 : -1;
   if(!g_in_position)
   {
      g_in_position = true;
      g_origin = g_expect_rev ? ORIGIN_REV : ORIGIN_STOP;
      g_expect_rev = false;
      g_need_reverse = false;
      g_reverse_bar = 0;
      g_best = PositionGetDouble(POSITION_PRICE_OPEN);
      g_last_sl_try = 0.0;
   }
}

void Manage()
{
   const bool buy = PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY;
   const double entry = PositionGetDouble(POSITION_PRICE_OPEN);
   const double cur_sl = PositionGetDouble(POSITION_SL);
   const double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   const double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   const double pt = StrategPoint();
   if(pt <= 0.0)
      return;

   if(buy)
   {
      if(bid > g_best)
         g_best = bid;
   }
   else if(g_best <= 0.0 || ask < g_best)
      g_best = ask;

   const double fav = buy ? (bid - entry) / pt : (entry - ask) / pt;
   double new_sl = cur_sl;
   if(InpBePts > 0.0 && fav + 1e-9 >= InpBePts)
   {
      if(Tighter(buy, entry, new_sl))
         new_sl = entry;
   }
   const double arm = (InpTrailArmPts > 0.0 ? InpTrailArmPts : InpTrailPts);
   if(InpTrailPts > 0.0 && fav + 1e-9 >= arm)
   {
      const double trail = buy ? g_best - Px(InpTrailPts) : g_best + Px(InpTrailPts);
      if(Tighter(buy, trail, new_sl))
         new_sl = trail;
   }
   new_sl = NormalizeDouble(new_sl, _Digits);
   if(!Tighter(buy, new_sl, cur_sl))
      return;
   // A one-point step sends a modify on every gold tick and floods the tester.
   const double step = 10.0 * pt;
   if(cur_sl > 0.0)
   {
      if(buy && new_sl < cur_sl + step)
         return;
      if(!buy && new_sl > cur_sl - step)
         return;
   }

   const double min_dist = MinDist();
   if(buy && (bid - new_sl) < min_dist - _Point * 0.5)
      return;
   if(!buy && (new_sl - ask) < min_dist - _Point * 0.5)
      return;

   if(!MarketOpen())
      return;
   if(MathAbs(new_sl - g_last_sl_try) <= _Point * 0.5)
      return;
   g_last_sl_try = new_sl;

   const ulong ticket = (ulong)PositionGetInteger(POSITION_TICKET);
   if(!trade.PositionModify(ticket, new_sl, 0.0))
      Note("modify SL failed: " + trade.ResultRetcodeDescription());
   else
      Note("");
}

void OnClosed()
{
   const int origin = g_origin;
   const int dir = g_dir;
   g_in_position = false;
   g_origin = ORIGIN_NONE;
   g_dir = 0;
   g_best = 0.0;
   if(origin == ORIGIN_STOP && InpReverse && dir != 0 && HourAllowed())
   {
      g_need_reverse = true;
      g_reverse_dir = -dir;
      g_reverse_bar = iTime(_Symbol, PERIOD_M1, 0);
      SendReverse();
      return;
   }
   g_need_reverse = false;
   g_expect_rev = false;
   g_wait_bar = iTime(_Symbol, PERIOD_M1, 0);
   g_placed_bar = 0;
}

void Arm()
{
   if(!MarketOpen() || !HourAllowed())
   {
      DeletePending();
      g_placed_bar = 0;
      return;
   }
   const datetime bar = iTime(_Symbol, PERIOD_M1, 0);
   if(bar <= 0)
      return;
   if(bar == g_wait_bar)
      return;
   if(bar == g_placed_bar)
   {
      int buys = 0, sells = 0;
      if(PendingCount(buys, sells) >= 2)
         return;
   }
   else
      DeletePending();
   if(PlaceStops())
      g_placed_bar = bar;
}

void Paint()
{
   string state = "flat";
   if(g_in_position)
      state = (g_origin == ORIGIN_REV ? "reversal " : "stop ") + (g_dir > 0 ? "buy" : "sell");
   else if(g_need_reverse)
      state = "reversing";
   else if(g_placed_bar > 0)
      state = "buy stop + sell stop";
   Comment("Stop Scalper  ", state,
           "\nentry ", DoubleToString(InpEntryPts, 0),
           "  SL ", DoubleToString(InpSlPts, 0),
           "  trail ", DoubleToString(InpTrailPts, 0),
           "  arm ", DoubleToString(InpTrailArmPts, 0),
           "  BE ", DoubleToString(InpBePts, 0));
}

int OnInit()
{
   if(InpEntryPts <= 0.0 || InpSlPts <= 0.0 || InpLots <= 0.0)
   {
      Print("StopScalper: entry distance, SL, and lots must be greater than 0");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(InpTrailPts < 0.0 || InpTrailArmPts < 0.0 || InpBePts < 0.0)
   {
      Print("StopScalper: trailing stop, trailing arm, and auto BE must be 0 or greater");
      return INIT_PARAMETERS_INCORRECT;
   }
   trade.SetExpertMagicNumber(InpMagic);
   trade.LogLevel(LOG_LEVEL_NO);
   trade.SetDeviationInPoints(BrokerPoints((double)InpSlippagePts));
   const int fill = (int)SymbolInfoInteger(_Symbol, SYMBOL_FILLING_MODE);
   if((fill & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      trade.SetTypeFilling(ORDER_FILLING_FOK);
   else if((fill & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      trade.SetTypeFilling(ORDER_FILLING_IOC);
   else
      trade.SetTypeFilling(ORDER_FILLING_RETURN);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   DeletePending();
   Comment("");
}

void OnTick()
{
   trade.SetExpertMagicNumber(InpMagic);
   if(SelectOurs())
   {
      RememberPosition();
      DeletePending();
      Manage();
      Paint();
      return;
   }
   if(g_in_position)
   {
      OnClosed();
      Paint();
      return;
   }
   const datetime bar = iTime(_Symbol, PERIOD_M1, 0);
   if(g_need_reverse || g_expect_rev)
   {
      if(g_reverse_bar == 0)
         g_reverse_bar = bar;
      if(bar != 0 && g_reverse_bar != 0 && bar != g_reverse_bar)
      {
         g_need_reverse = false;
         g_expect_rev = false;
         g_reverse_bar = 0;
         g_wait_bar = 0;
      }
      else
      {
         if(g_need_reverse)
            SendReverse();
         Paint();
         return;
      }
   }
   Arm();
   Paint();
}
