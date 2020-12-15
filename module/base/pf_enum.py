from enum import Enum


# Maturity
class Maturity(Enum):
    M1 = 1; M2 = 2; M3 = 3; Q1 = 4; Q2 = 5; Q3 = 6

# Stock Type
class StockType(Enum):
    etf50 = 1; h300 = 2; gz300 = 3; s300 = 4

# Future Type
class FutureType(Enum):
    IF = 1; IH = 2

# Option Type
class OptionType(Enum):
    C = 1; P = 2