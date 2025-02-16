import QuantLib as ql
import pandas as pd
import matplotlib.pyplot as plt

################## BUILDING EURIBOR CURVE ##############

# Defines the Yield Curve Input Data
today = ql.Date().todaysDate()
ql.Settings.instance().evaluationDate = today

# Defines deposit rates (short-term <1year, eg euribor deposits)
deposits = [(1, ql.Months, 0.02653), (3, ql.Months, 0.02526), (6, ql.Months, 0.02468)]
# Define swap rates (long-term >1year, eg euribor irs)
swaps = [(1, ql.Years, 0.02264), (2, ql.Years, 0.02145), (3, ql.Years, 0.02140), (5, ql.Years, 0.02165), (7, ql.Years, 0.02202), (10, ql.Years, 0.02261), (15, ql.Years, 0.02314), (30, ql.Years, 0.02067)]

# Constructs Deposit Rate Helpers
calendar = ql.TARGET()
day_count = ql.Actual360()
fixing_days = 2  # Standard settlement

deposit_helpers = [
    ql.DepositRateHelper(ql.QuoteHandle(ql.SimpleQuote(rate)),
                         ql.Period(tenor, unit),
                         fixing_days, calendar,
                         ql.ModifiedFollowing, False, day_count)
    for tenor, unit, rate in deposits
]

# Constructs Swap Rate Helpers
fixed_leg_frequency = ql.Annual
fixed_leg_convention = ql.Unadjusted
fixed_leg_daycount = ql.Actual360()
floating_leg_daycount = ql.Actual360()
floating_leg_index = ql.Euribor3M()  # Set Euribor 3M as the floating leg index

swap_helpers = [
    ql.SwapRateHelper(ql.QuoteHandle(ql.SimpleQuote(rate)),
                      ql.Period(tenor, unit), calendar,
                      fixed_leg_frequency, fixed_leg_convention,
                      fixed_leg_daycount, floating_leg_index)
    for tenor, unit, rate in swaps
]

rate_helpers = deposit_helpers + swap_helpers  # Combine deposits and swaps

# Builds the yield curve with linear forward interpolation
curve = ql.PiecewiseLinearForward(today, rate_helpers, ql.Actual360())
yield_curve_handle = ql.YieldTermStructureHandle(curve)

################### Curve plot ####################################
# Extracts rates for plotting
times = [i / 12.0 for i in range(1, 361)]  # Tenors from 1 month to 30 years
dates = [today + ql.Period(int(t * 12), ql.Months) for t in times]
zero_rates = [curve.zeroRate(d, ql.Actual360(), ql.Continuous).rate() for d in dates]

# Plots the curve
plt.figure(figsize=(8, 4))
plt.plot(times, zero_rates, label="EURIBOR Yield Curve", color='blue', linewidth=2)
plt.xlabel("Time to Maturity (Years)")
plt.ylabel("Zero Rate")
plt.title("EURIBOR Yield Curve")
#plt.legend()
plt.grid(True)
plt.show()

################### PRICING FLOATING RATE BOND ####################

# Floating Rate Bond Parameters
faceValue = 1000000  # Example notional value (1 million)
maturity_date = ql.Date(10, ql.January, 2026)  # Maturity Date (Example: 10 January 2026)
coupon_frequency = ql.Period(3, ql.Months)  # Coupons every 3 months
settlementDays = 2

# Defines the bond's schedule
issue_date = ql.Date().todaysDate()
schedule = ql.Schedule(issue_date, maturity_date, coupon_frequency, calendar,
                       ql.ModifiedFollowing, ql.ModifiedFollowing, ql.DateGeneration.Backward, False)

# Defines the floating leg index (using EURIBOR 3M with the yield curve handle)
floating_leg_index = ql.Euribor3M(yield_curve_handle)

# Creates a floating rate bond
floating_rate_bond = ql.FloatingRateBond(
    settlementDays, 
    faceValue, 
    schedule, 
    floating_leg_index, 
    ql.Actual360(), 
    ql.ModifiedFollowing, 
    settlementDays, 
    [1.0],  # Gearing of 1.0
    [0.01],  # Spread of 0.01 (for example)
    [],  # No caps
    [],  # No floors
    False  # inArrears = False
)

# Sets up the discounting bond engine
bond_engine = ql.DiscountingBondEngine(yield_curve_handle)
floating_rate_bond.setPricingEngine(bond_engine)

# Ensures we add a fixing for the required date (archive rate for the bond)
fixing_date = ql.Date(13, ql.February, 2025) #The fixing date must be adjusted depending on the current day
fixing_rate = 0.0238  # Past USD Libor 3M fixing
floating_leg_index.addFixing(fixing_date, fixing_rate)

required_fixing_dates = floating_rate_bond.cashflows()
for cf in required_fixing_dates:
    if isinstance(cf, ql.FloatingRateCoupon):
        print(f"Fixing needed for: {cf.fixingDate()}")

# Calculate NPV of the bond
npv = floating_rate_bond.NPV()
print(f"Net Present Value (NPV) of the floating rate bond: {npv:.2f}")
print("-" * 40)

# Calculates clean bond price
bond_price = floating_rate_bond.cleanPrice()
print(f"\nClean floating rate bond price is: {bond_price:.2f}")

# Calculates dirty bond price
dirty_price = floating_rate_bond.dirtyPrice()
print(f"Dirty floating rate bond price is: {dirty_price:.2f}")
print("-" * 40)

# Calculates the present value of the coupon (using the discount factor from the curve)
for cf in floating_rate_bond.cashflows():
    # Print cash flow type and date
    print(f"Cashflow Type: {type(cf).__name__}, Date: {cf.date()}, Amount: {cf.amount():.2f}")
    # Ensure the discount factor is available
    discount_factor = curve.discount(cf.date())
    present_value = cf.amount() * discount_factor

    print(f"Discount Factor: {discount_factor:.6f}")
    print(f"Present Value: {present_value:.2f}")
    print("-" * 40)

