# V6.46 Complete Pool + Final Projection Overlay
import streamlit as st
import pandas as pd
import numpy as np
import requests, re, unicodedata, json, time
import concurrent.futures
from pathlib import Path
import io, gzip, base64
import urllib.request, urllib.error
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus
import xml.etree.ElementTree as ET

APP_DIR = Path(__file__).resolve().parent
APP_VERSION = "7.47"
V651_BUILD_ID = "V7.43-ROLE-CONFIDENCE-DIAGNOSTICS"
st.set_page_config(page_title=f"Fantasy Edge V{APP_VERSION} — Unified Contingency Engine", page_icon="🏈", layout="wide")
CLOUD_LEAGUE_KEY = "griffin-main"
_CLOUD_DEFAULT_URL = "https://awzuvvzezaxewfgzdqra.supabase.co"
_CLOUD_DEFAULT_KEY = "sb_publishable_ahyUJJT4kps3Vt_qHAZD1w_6XthUAUA"
_SYNC_STATUS_FILE = APP_DIR / "fantasy_edge_sync_status.json"
_V651_BOARD_GZ_B64 = "H4sIAGUIk2oC/719W3MbR9LluyP8H/A2LxCi7pdHSbRli6KtEbX27rxMNIkW2SaI1oCANPCv33MyqyFAnzQcrx3rCVEaEp1dldeTWZnF16tu32/mr8eHYTuM6/lFt7nrt/98P1zfzX/5+c3r+dmme7f958P1uOnnz8Zus/znePXQbz50/PjD/GJc9qt/brq1flz/9ax76P+5Gj70+ty33zy/3QwP26Fbzy6un3fv3m36/fzNs3lepDy3dlFMKsG6kmywwbm5zWHhUoo25hCstXFuTTZzu9A/fuFNdDWm7GuozpZvv3k2/Abib8arYf2AXYC2XcR5XaQUjE02RltjdmVuQ1ngJb4al6x3wZa5K37uhKrB3zl6Vwv+56uPNYVvv3m9u+tmP3XXu27+6xt8ylmsZhFSKB5kojW15ATCGYTxmhJqxPe9n+cYG1H+KSZW51NyLpfgTf72m5fd7f1+M3sxXF096IrBjbrwKUSsGUSscwGEzaJasCXElHLyOc+xwHkA0SCEkzPZ+pxqDTmkmkB4XHfbW/DjbbdfjRvSBlk/L4taDV5uDXjrPLjhEziUq7fZJa5rXpKfR5CNQjrU4nIoIRfjS/ay5n+P69nl/bC9ffLTb8PNlTAlLFIF9WBSxM6DK85ncMnFBZZtYzHFFwh4HqKfJ1BOQh3biBB6zRlPBfvtN2f9334B9afXWHsvHElcdl7UHEu2+Ez2oEbKeGOxYFQmAYrVZ3zOyB9QNjliPwZvBicrl/03KPZm9vwWmskVC6/x4exiNrnYAIYETzXDpg1UI5gSwRF8x2FnBgyk7lXHz9ZsQjHZF2jHW6gylPrZZlj287ffzW1dBFJ2IWRyDwocsX3QiQsobIwlhuAqNSbFImSLkC7RW2+8rSCMP46Lvu8fZs/H8U54YRY2g3PQBJ9pKlhghjKALeBPCdir89UlH+bR8H2kqhaTc8pgFtZefcFqvv3m6f24fvKmm11uF7Nnm/HjmjyJixTwAiwvZQoQ/8Ae57UuIE9oSQ7R2WqhJK5RNko+xGAqxG7Bcws5vukebvt+9ma4Fl47t4AFx0X12cNwYTfWGgPCflFjgJkZmxPUYG4jtM/SXPTLIuIb8AMWO63OJPoRyK+tmDxxYgWpYAnFuWQ81gA9z7S2mCFAgwXTDCkB2qJNQhjqCPfhxBKwFGrI+HA7e7pa9ev535/NobklgXIWLYJKWwsWwjoWBptwWDQ2UsAusBWUaYg2KmVnodSw84rFh0Cl3mzgTGc/9OuNOD2XKEgKzcFaIxyHLdWmeYkLl2PAgmAr1UE5QMk3ur4RLzGaFBJcWqVen/fDcjMZ5PzsmVg0WRJhdhkuyoJvxcA4AxSnlpKgufCxBd8wEzeof2aBn2FXeMaWXOFUm9Oe/bzqPqgYzSJy3XBeLiRjfUkOjnpe6J8qVBByBFehe6AEF07SajXOR9AGWZgqnEME6e5+dnnXbbf91UiexLCA88EaIRdIEcaSbYXDAG0PnwWpQkdMgDbCK1pdsmvhAMpBK890qt6D4y/6cXPTz16D6z0iFK0dKkyXCdLRFrAd70l2nmmrkBNeCpVPiAS1LTm3dZMknCve6WNsSvKyux7VYQd4dQ+yHk7IxRCjzyXFMM9wtFDoGJxBlAJpmICrZKDRL3ZhodMmgZPwD8UEGvuHcb3tZ78Oq9XQ3Qt9l0nfw1XRHmkDLkM7SD8HGFtkrMmwLQhN2eGCUjcIBpXCAHeg51CU/aZfnxD3jmoIE8TnkoMCIpYVR9+VFngTfDl8F7QFLgYCoBEb/YL3VHySwQwRB+r+7Tc/33cboIHZD939+20Lv5EeFpEajgGMSYg4CFGGUXFBn4sNgeV4a5rHuZMwqaZpEOPAMwZKRvhIJb8X2qvVsYaDJ/SVtnoIP6V59ojJ9CvYNHQzJlVx5UgQFWdsp7eB0WNbwdN7dx+g499th36tISckgQLOB/omOGrYBDgzz4iGztoMNwPH6A38N5SZjgLvUAuqDNIJn7AMHhZcB3a662cXQFh0Kr4ubGVURUSAr8q5Ai9QX1JdwLNG2TOU0cO94v3KENktrBNxFJYZHQmD9d9+cwHrue0/woUDT42bJd/AWEBtQ6RBjIHVGWAIiTMJ7jcg0MLfwG4RDSBURDdHRfdeXgEp2QijQ1Dx0Ex4F/hZOK7Xu81yT+rw15FAxonfjGCMN9CMREnDpeBbQD2u5HmBZihTvBXSyQJ+BYA1rAegDqTP/vZ0vdz0s8uPw7uteACN3GA1XBQsjmYHE030k1AhfAdLgw5Bz6nstFL5AqnC6gjC4LdMqJXr3l3f7Wc/bj4M65tGG94cjIf3gcLBy0L/Qg2kDl2EiQA/ZUQ7+PPssGraqFedSSVSyzI/luA1JOJ/GDezV91HmNS1SDY32BGAChGeyQxbPOwSNlbwKHBZgtsBw6GSQbniVWkgdazewNLoDhiJ3mL1/WZ2TtxNRAH+evEC4EmkKRlEDXA5YevFMmQAEiW8Eb4Fjt2LoapIYR2JEQxBKoD3IP6620o0uuhuR6ALEWtYCALGEiB4mBxYCRzk+ALYoYuAigjuGVEE0MWquvgsLwBWwqrgoYlYHP3YWfehox97uqSfIaow6gjgY4DFPVwiDJC04MSg9JWOHv/I2CKUSbguRkXBQjBgORAo/EBBRHq7vwOuOAl2hdCpHv8HqwRtrAhwBfYObUKcjvAS+Dxd49F/Tg2AQQZOA7AO+g81LoX+eL+ixwRq7MWhZQIYYnm4bgMXUJCyeOQnorl4DV4FQcLs4BnwEzXc4JRNwCcIxoi/JRARf/vNP7r97PvV+LHfCJOgyp52Cwkg8YCNIIRSzPMI4WNBlttAJAe4ycp7rzyCvOhbTUhAfmAlF76hSxOMtOr7Ty7TETITPcKTAGaA4RHen2GzQLWZbtU5AENWzfS6cgfkD48Gq6C/joFOoe+ve3XHGqMEAwLWRTommApwFUkjKwLDLeKTx9bDvNIBgiVqVzAKyASpEjZqkegItkMY2QxAvPDFG1l4IgakzyHWgEODmxRHM4/8ARQOKA+mC38Kxw1gEMRyjbwB2ASQMDJBo3UIWlqv97MX3bD+2OvqrQGdSqQJpueC8B0kPQp8gaM2QBTIxBwUFv+eB1puUJeMjAmvJGcADqqFS35BZdluGWaZhDJbxMfo8qGNgJEZL0GghUuYB7AihgxnDtAO5wbPoMoS1GMSNQCpI98BN2sRf78a7pCHXk0qU5Q1VnI5IkKsGygEMoQaEX4yC7KMXRXcEaNVhwk/Hxh88GEoLrM6IPVxdjZ+XK4kBhYhDbiJxRqCJSgJ+DBHigs3TLCfkNBlOnkkwyLQoKShXLDwkLFygKkKdfm1W//trFv1n3JzrB0AnfkhdgnVo3YjXiOaYO0wMsQlRLsI4AQvNMdf/K7hy+UNDpi2Bg+20GFDqn/fge4tEMLL3fIO/+QO4LpqlcBDh4NdMHcGp4QUbAXuGbkj0KAHcKgq0WTbC+BgK7MSxFAC+OdY/dUn6ASPmWAgmWYNFIHAE0IlQ7lQRCvofIyIWAmREM4Jvk9WnlRpwEs4B0RJ2JSBYwPvofajxsJt/6GfyhfFcgd2QYgA+0ByR/8CJ4F30Ibhqh2hAswY/p9CN/oFO4AnS1BkYJdMXAufsHvYDoBQ/Qbas5WIpTYCDXfYBZwwAGWj7lgigCbBLINyh7JNrq3fMOsk6oSMPDFxRz/5w26zFd7EBKBBwAJ/FxF9AkECUnxREzpA4HioFJI6wj7mqqw2NNkSzmZYBTgDGSTJbx76bj37afg32EKPkOHuqfXAKQYhH9g50Xg84QuxHxNUhHHar1F38ARf4CcAhBDygcxoTOdw7kgQtlgzImyhg5GSALAVFBhcIyLwJItvIPNE5gw7D3Ttbh7FTmPTFmAeLArZuIQQgQe/9HsC1n69hK2qOOkPPdkiKRl8DUIN1ptp9AHUET0RuSIAJzEIP24kiolNMegTOmF9+B9jLFDZpn+4HrfbBj+S6CO8OhAeIA00jBUo7B9eqyAuAF64KhCBuZYRFcYTxKn4IYFZYm0F6vgSrn3zQetzlUhShAmFhuiAnqAd1pEwhAc5IuwhtwNSR9LHYGWoAEKZYAnGCplCRqT8FqH7h+HmZtCczBPCs6RC948lIAVzhNVwUkArCe9zrPrgO0FpBsU0HngHphnpZKoUdy6G69uuXx253UonR0QOA8+MAHBGCJ6Ooc3DkPj/YR5QTbg5l1T/okoUbtnjHeAlPEFRB9OvaT4vx9v1w7Z5MC3asN7hC3YJeAcvniR2AoU61qoQUD2rJUh6RJTRNJ5zqzA6R+8OxoDf42o5+75br4c19REZWKX/hSuBCQOOJYgTORcjP8sPgOfQY0Qd4GPoCs0zKnMYAhALHACfSOy48vprt23sATsjWU/UCJ2FqWaG/yT0EwspACFIjOHfreBMozpP82c0jSysQcsIZC6Ryb/qXo+bbddMKdBtOZaOgLAi0gnELwF2mUxlTDNM2yBodbnRNr4zyiBQu0jvw9Jav+2GzdjNLq4v4H07jah+kQU+MCZHX4jXRG0Cown+5eBkAHAA7dRnpcYZoKSAsMUEDgboW3ltPEqKyRmmONAbeFj4H6gHPC/QE9+aoDCFlQnkENR3vFppRwU0gAKM54iWiVUaotURaOP1iJUjO6NLN2qmkhYhpppIdOWZ14AJidmImWfbXBaycsTuirCCJJTJ5Fv4rM0ESMFqrBVwH6xgybyQGZALnBypI6ozyYSrAbRG6hOYRRj9Iu6QSTByIEBsfIGWjPDf4PBydrnbTirO6i2NH9GZOXwkeoWiENQQ5uGfnsXXapk1aYATXeTqAT4SMyGW77AF+BWkG7Ofl7v171JMwgetE/8ZQBxuxPKDrHbgYZgOVshajfesZCJ9lRA6ESfkgnrFCM5Bz6UqTUmedRrckKjiOXyS6VGFJ2JOCaWuxNnI4kyBm0XakZCiOae+kPVZoQ54jtSToaUwgaa7PZ9d9NvrbvWOK89l4QSgAS4CmXvHpD/xGGEB7YMGZJCCL3ARftnqokWyItTAsgIcEHaHDR+lGUtiL+p38+VYnqf0gZEzTDqSPnhKR4NcAE5X4oSE8RbLWVNIAGeeOL2GcKhunPera6lN10K+UAvhkCtIWFoi0LpLC2iD7AZ/sxgZVBFTC6AEmfixkXzPssY7OV0G0Xs1zeKpMPw0gCdL366Af8g/pQgDq8siMKQfiPuwIdZUjEBwZTx9BnN8qedRK7+77++62Xc3V7s7PXuRmtITHr6AVgSvIwv92BPy3cwTE89MMmvJlxUhkveN9yziMTsEi5BCsL4+9rNnuw0SJSoNAnoW4lCPhFyDBzXAjnSCcAqJJ0YOYsMrC1KZLGUlEyb2AAAQUyPfhl7KOcl+2VMj10O/EmAEFAU8+AS2CQgQghSgMoK+LB5GGOm5oEqFKSWzTZbvzcQagGnkDXBFSDkT3Por5kosRd7Rp/9dynne8rOVik1MjaQZQkss2kmxrTJOF2JPuMYsxTaT2voDhYqoAbPiKyZU96ZfEpvOz15BhBrXA8s/nkXkwsKMVDUBaaHODIJe0mzwSUsiYrZP+AHoAkGjp1kZzzrE5k682cPtsL5pHidNLGKBGasBkxIcFWE0EoZAc4NVAE7CaBH+aYpGjmzkJT5gOYAysBDESh4KPl3/C7nB7Fm3WfcP3IRt1TSp8CbI69N/mUKtRw4YOSs0qnjCBPioRHLbW7r0V7vr7nFy/jFyzzbwt/Baz1eA/fS9j5IEgHmU5h65+Qto3bh7fIks9v5nes8RI3m+gOQNiQNV7c+v8ezljAnho5SsfZQSM6fh+lMEf4zko/s96x+o8LNX8Gr/zRLTowRHLvFfO8Q+iPvmcZL50TW+6K56Wv5/oYO0kf9MjB5k9np/tdv8F6JNj1OTOHwxDo+zTpzEI+TGdXc7e9t96B6n9/jaxofbXQcQ/9C/v32cdeVR7Xv1dvbzB1jFf2EU8VHf8qq7G7DTh/+CcY+y7eLl7OmUev4VYvhp/5vUnoAjVvvHde5RBzDVoF/2a6nX/GnH/LrfMpaM4/LhL9nwm9lFRz1+ezved38NybcvZxryHlfkRx3A2/H+fj87263/Cm/cMOLlbffxcZt4jNgv1DwJko+HR//oPn/tH1b9/r/37jx5/c8U/9GtezAOnnj7OLVHzaxbdde3A7wdW6NYm2rnFnKujgw0aPMBkJGhkpSGtw4UE1tqWMSIiaCVCe9mw2aSV91uMwgiCqFlMsihkW1VQkCsmtl7YpcLYKOvSPSQU8x9g0LWuAk1sorl2DhkmCi1stcP3f2w2rZymi1STvvsBCVJ10GoLJR6Hu6ZKi1YViCpPWIKMh8WgwGukUkWMoWnbiwhbYaHA6oTUEdAVz3rdVG7PQxPyVlF4Dd8CHgFeSQH8KZOTKqBzUcRawH3PSHJRrL2fr39XQqOkrd54nvPtMHyEIcldtAnKI3IwljvRUZEFmnPSmgsihXJbZWf5hAo1OGun333oVtPZ1dkv0Wuiuwe8BmZKTI7rLSwVQGr9MzjgbeRbIC2NsWUtnS8XAoGLjmWa45ypk2nhTspfXDtUBQe7iAFKgW5ZFwAwkb2GPHRXCrCm9WeGNsYkyhVHvMHSD9Re55Ky9c5XHV3h4xskKyjuK+9Ad/x7B4IPCpmw1AFcX/8isxepSQZHwQcmvpcXD9vp80Cv79AOyyQP2FVlvk/uBNk9eGUtHEs1iJnYlUBinM29DcjfOSHoZN1m6/R5jGNZarB4iJPq0A1ntJmPZUnKyYiheB5cH/L7oeLUYI1qbPM82XqkBf+b7aFjTAsD3Lt6YR+ZvOG5fEP8qUi5YfVeJLrFdj/l+kH2jpS+sKejjkr1dprciCOPbFl0ctBPVueXu2gkU9X23u2aZJ2/hpnYEE8OYzsBjPsUqxi3yfUQ8ADJiHdi15atUYelb8a76+6zXIQqdqv0bfMTb23bIqQZrlG+BN50uYBDdurUgL5891mi+jyZtwh9snqv0KdrWClwl7ZDRXYFEil0WaZT4yHIwDLeWrFY3VtI2JpsHEmfVmqfgE9pvOM0bCyxHoVaNsT2my2zLUEz+JzluYHFk0bBGDdJ7NFCb4gw2MgjzYmIB5UUAN9yAyOOWF9LL7O2bCqvTLWTuZKyUNpWW53AkcR2p7e7IZVJ4tnyfrLi4dKsLJnXYDwMhsZmGKfWCoUxbMzkU0NUQ5TkWT9r6G7QZ616odD88aX6bOeFKKBG2T5YR6lvfKYOo90IRIbuIbsmdUcmPP+gZ2E09ne359pZfyLLwpsimMNmI0UbI6lbbl4uhEe+gV2oCBwuaj15R9GOa/lyVv6KnHWNHkaZHm8xA4aVvZPRAyPhJ9FKx2t4ROQ6n8ZtqO447pIX6ZusCj4nATtgft3XsmfWq7hmQIdQmABqbSldxspj6nTYTD5n+QddN9n+IPK2k7C2kT3Ty0XTth5GAi9TuWZ7ZSqvhmWy/4/qpCTevaRCmU1gHoqZLhhHpMbm3n4/O03PL/iMdY43in9bL66AfgF+BxwNgX2KNI1ePOZw2d1nH02iWUycGfbs6Awe8bOKw2HCFZf2QDceAaEkXofQAOTIOs/M+AEyRSeJQtMggF3A+HjP7r378X11K+4HoddeR5qwnE5dlqzx8L6k2hbHLvj8BhCD6tSKtzvblcDcnplTvwadZBl/wf0zkdv2GME6qeBFj9h7wi4QykVaRrt72aAOkJbDne+QJtHxIHnhpVrz9XN2dJ9GmjhpuiT4awoGZb62UF73vfr3X1zml8WKgAb5clzXjYWR0l0QP7UXvFZg3jgKNNspUVys4RreLpcTviP/cMCoiqYC9sknHAEpFJ59KECG8FtsYeULekNlSvcUZdgoDxsCmSLFr3+7e6qm/2wu7qaDlaSvMGxKR+IBdbHGOgdv8U+LLpeHipVOe+DF7deTdcfpAsGGfadmmyiZGsw3KU2/mhYYfcMdByxu7I9FrCU38PaPeI55BqztALzvMKr5bbzhEIUxZNNcBFh0UobynYDGPhst1oh/MpBq3ieL73DA0zBonwAGcumXgIeX4/fwO6DYoCj4N9yjW4aAKBxbWC9D20XrJ1/+RWwTAIDtmKxsXnexg6Od5EhqciTQR5LudYKezZ+VKDMsyJhCLOZQiHDO/KI/0kBlOWIRuUxdMZG5nQPQW23IWX45CJ9ZEDXqUjPhbQevxiXHzUPKuwyJ31mUzlBSkwLCvMKOCU8lVkX9+yH4AlyA/gKOp/IOXDlmAMPxeAfVEv3CGD7KUeRUxcyOyHCAnTbxKZCxnu8mccZwOKW7Srsfee4gWQRoj/YCtIjy5bLTN/MJOiuG2av2LYqi69fJc7O+Jg53oCoIpjKcfHhhDpyFEcwy4ED6RX+aWRZ7IBMamSC9WXyjnMCSC4ltgTmVSAcj8lbpoaGAAJQHcBKOhiuxs3sdb+WU5c6eYgv0UdWVLJjBwxkgjSX4EdOCj7Rd5RZ5JkKtElzrFX/MDsftg/9irGRx8ZW3gGMCVYEqgoyM0BIiNxKpgWZV1gPjVpnbUz7ysQyIKvjKSoP7IAfBZAjCX0+rvdsluLJ13+iz3EKJx2kcAOM7V7GhI7fwP6PTAdR2fQl7dq3/XCP4AVcwvWXr9KHDDI7HwFPIARjGVyko+YT9QLYDl3FHzZLT/Idb4ZuaMwxX6PNFnx2HyLtxbfnkG40J7RpK/CsUE68hf7//BbMWc3OBi2+kX786uI5acVGCHY0s5QwdxxKOF18RJpE2A7mp8pmsvHhYaZlJWlmyF9bPRApj6Fpk/DSMsYD6u6EeqTRgi1secgcirnYU3lap50UceQQDhhcKi8fOD816/+97TfrbjWDPNPsx7PXs+tx/dCvH3YPs3fdanXVwe1WcG/Oh5A6D4xZP+y217eKY0nXatNkTX+UMMswCJVK+qL7979nzzfjw5XWxKyOmrnwx6kSSjSqrIkdiryzl5uF0HY6EOZPijk1/uE3WbbV6os0C3q227Q6rc4wwJ+dvOKPv8GSr/qKn1gLfjY+dPKC1sOGUHRSkfrDb4CTQ6DXN2hmztLXbr1tJViB106bEP4YZXiMNFF+u3i5YGPNUTmRjakna//j+sMGjkl/JM7+MKz7hyc6nYQXzf8oxYlW/+5dv9nPLof7+7EJdGpNCObkP/+HFy2EGlc4E8f0gWX+yZxaB1Hwf1I52U/+mXZuuvW1NoRDrxKtq35ZPfNn73jXrbfdw/4J33X27MtWh/h/rKjf3SNkfUT+q++LC4f32T/1hriok6L2m49sNGNnklaUgWmZXv0Z+gBB/ngHdEaNempTniem5v7UywrA8qRtDw9DP3vWbafNEOS6v1I4zh2E83S9HWEls1+H9TsY+1Kd4jNJtZx0YJ9ssvyp16aDxJ6P4/t+MzvrX/adVtTZc8le0tNd+j/zPuRc/qAhH6RlbXsL1/9+bFV8BYyfCbL+Ka1EihEP77xkLvHdajWw4VReCLzMDPGvE2XwB1H+b0AH8PTi+nxYr/u9vJDt+DJ59tdJEXuYpPhst1x20NS7NnbAcUR2vn1+KvIn3gb399noSbOS3Yo+7NX4Qc+QYlkQGvyV6hPTQX0+dYO+GNe/d6v+d3lpaX1G8SQG2D/FXqGpb73sdtKVsllOcx0lteTga1Hn/+WF6fDC1912drnbbDs40x9//P/xxrN+/TtbkFmR+P/wuovhGinCazkKa3F86tRzpzJE7Nefzekjl5v+4+wXih/wv18patGhznIamPkc/FwofPCngQhtPWy3o4I007qfTx4JfAYYyCY+8xaKPXu7G97vVuN2p49pp+ypalfHx6QggKee9/1Z389edfdXMrjLkmairxGUn2MbxNf3F3cYbVBo07J5qetgHWx41IeOh8rZcv304XZL4AynvZVOdwRJjqhHTsO1Rw6Do5xToRL/azdKM9ndqp+e4UUJZV7z9Iz/NKudpvnJZzrlhVTI6W4Cyz3tAXs0pX8YGH01svIqOymyLMcaQnsifZo15wTruZRPb6F5KzbU/Qh159IKeMaoIUVPeS5+2g57K58SuR5G/50O0nMsfPp8OZqWtwIdRmTUiAFa8ZG6fcBbyuENx5PTkSbxywidbuN6epjN1OfQtWp0eKzNKvLIZeSgh9T5fUPSWvvkZz+NdsGqGHhX7MUXxynNc+CvFB5EIFxTPQixCcSxzWa5lBNMaP9e1iRUF60XtZo2fOgUrFYOAvab/n7Yw9zER3PkTe/e4ChJjIFj2Oz0Z/U6RzbIs8dXRhlk2jsHoydmPGVxHNMuJnGaDo8lDsqygMESEPvqM7tUnUxRDlgo+Hcz3vd6b0AM7dYM1hNi5fhYwWtj5aBk9hxUZ4cqnLY0ynqedRQOcIYkkyAWyTSWjM9YXrrAIMNBrlwN55ZZHoUEbrv9w+1uBcPdavUzap4UXagp82qTAHKJAiJdx7sKcnXcq5eu/8jZI04RcxSVQ8fee1tLLjZmmcjKvNbF4ItjUVN6DDdrZGeztwCKUouLU2UhuMg53SpTSiLGxCFVOeXyhqkbTa+Cl+xedYYVcOn3zSHFaAqHLGLSs/iIBVVn5PCVt7qcDF0IWOSobStIOo6NGM/2e4iXvQ+AriFznqHg2yyPG5okp344V8Q+gyIHPIED3FHmHIr0QjuOJ2C5jrM7VWpTy07Sltcb3o/ByVJ1iz6z9ZwtBVWOfsk+MM3LhSqBZ/1zmdvJLGjjwzL6XngkFnmulrMU2Irs13CKnqUfkEsyjNAuRTjXxkZWfYKyGT8OvPbBsSk6gIORmsL7MdiGnRPzASlpcOfSChJ4FQbLESlxGMyzZq69x8lHz6PZxCKx5bH++XOW4a7799dDOw2YDkSxMsO+kWIMJzNoKgVco2mwrQRaTh5nnpjjLTyO5+yIFKtsdV7ug+HtCdId43MFhzgFUZPX4Q7pv37T98tWIjUsH1MNUuEJF6TKaV4r3Eak87xgwXKrsFCeQafM5hcwP0hBBJ/JnNRkJzyblHlqQ/MynLdh8YrHoh37asDj9XU3iEdqUwUs8wZus7IzOfNkgiOnsNlEGUKBEi2I7wmsnnNavhp5Mw8QZNaNQ9keqihHIlgr1DE5fNix3fzHh26ghxoQ1PfyYm0ddwsP31ML9uscp6FZx42egxsJz9tKZsz1QMdXGfLgRKNjwxLsjZVnTsV6HgM5Pc1gYzzVOecCsX+6h+AFzKnXoCVh44mc2nkOnqVS2LUkRm0TXR1vaDDZ0QvpQSQnkznLHCOPnqALnH3Bx9gu5HTTgQMZUAsxSVMPMj6aKWsnOtDMyjaExMo053eles1/cx4hSsGRL+ZUTwps4siOI0NBSmicuy0wBnhQuGU5PoAoeELoYdaZxxMIupzwu+yWw7+E2zLIRG5DkhlqDVfOy3ik6h95DQ1Yhpc0pyXcBjkHp8XeqSxJOkeJI6feoMdJeY1/sgOIdyfomb72mjFuFclqGSCJXBi4dGx7urWAjSNMElm7I5cIDNjRFNotV5x5a8/FTxc1ZJa2F+eL2dl4ddVmaYs5xGKJiidD0Nr1O91TdIAfMtfFdEKeNkY2vQhB/oKnltk8W83nN3CII9bLSeQWm3JEgIl8kcF0RAGulbeU/I+OM6EwRRHWxyPhBi/SkXGEZGQU1xsdy7eEUMedHtPjWS/ugvLw45DV3MgNAFg63DX0gI9Di8XV3I1Xw+yi37fJ7GKna5EEx3Dkht7WYdVFrusi3+BPwvEc6uxSQ1CpbcpRZu6kQMYgByfI833YHGeDvJcD7hXB4vNxs7uXM8SGjYxMjiLG8kkvO64EHTpLCs8J8Lfqr/HafqMXNFVdMLwOn/SR0Q04mGyuvO9DZ3M9AdRn90cwu9LmElk0r3nicV6Z63AML9Pg9RLCLt5p4v/H4NDE8Kq9k5WaSS8oayiy7JoWVVdvZLam1Qd+HTfb2307YdbrXcQakno0w9I9/yaM0/sAfHSnR4vTy3UGSZrqCDgTR3XVd4c2QSQ8sGy5E427m2ku9aBOvh1VU6tCho9TfefdRG1IKOiAlixfu+jGdbe+6Qa9hKDNEhuZES1qLqbKN+QwQXZv4PTiJ8B/eo1Bmy4PQsG3BRjROTYkWqeTpza6wxG9wFm5NGYaoIH4ZD5+8lGu6DqsLp+nw7r8zexit9l0civMYUgJbpUzugiL4tR5oYge43MbgklcSYe3S4e1+oowze+IV/FVF19E5xlLnIgPMMGyztdxHuXluO7VZIRCmppFZS476PadEQ0mJeBUWQEPpadBysvbcXdzqzuYxpRSJFAutrSwlEpz1qFNNQbZQbfpl9Cgd+/06TJ10EiS4sVk2f5C7ecqAMTkad5oxLYU5mkX3V7KlEph6qbg2FqFDYj6wSXnpHgEwVIpVJ5u6k0Q0hYt3YbaysY4FeR5K9CJ0a1w/45jedP4IRXwTQcL7JazX2+HrV6z56ZeC2d0IF0ZmBaFDHBBPLcuoHm8fvZ9v7nZUYa0ANcOe+m2PG/bUR44cZhyD2Bqg2bicXW67Lk0FtH8XFOBpO8HapD3F7VgKUMc5vglO1qtOtpwv+R1BrKAljRQCX0SN2K0WYVKiDwzqhLyVrSDE3gzLjfDza7/fQo7WhHnmXsSWUbVJAbHoAuKykmrfSLnfUfAdzFsr28nU5SDJVZ+ily4EXUvEAZtkGoRGyuIYnQulndv7K4UwbhJF6roIhNLI009NulKYpnmgymKdpp7edvdDcpLb6amCtOyvsYJ8SaMns0ca7FG+5jOkIGNTRcl8j7RWI23kvFGTtPEGXiNCjoRSm1+zjLC5XYz7trjTRECAiexSBRVpFk7XUVqu2e6SlOENfc8Lb7eH4TgW2YSg8gyqkPwVQxJrqxUFtjiQpmU6XhGXA/iJIUUdeS7jdSYBIH4IqYp2mCSDGtej5u9HIzc9fsnF7yxb7vVtbSDaLkWKqofle6SUHRNWdnBtsVEHD5IXQ7qcD0qgaYOjNzknqoD76sgQ4IRG5dmfbk9Qo8q1b8pQ2t7nr6BlShxztGpdwxKWBZQKI+fwc8la63LB0V9Yh2hJQNUAa9xyuhJmtHdFNUJTkvzQgI5Jm03Fsrzdkqf5NYt+ikjNXlxsNhMUX4i4WZzBO9/HJZUytuWf7WGezxghQ3RCgUeI5CPIYirIgXjiYt4odysna1MMXpqKEECJqoVVLVUmHLe2zjJEiiFuiO66Jnf36hthXAkTC+WZKQZQ/xsUHenssgyDNhfjQD59ztI5HJaRXM0DHM0agGWtoVtOVNorHTSifVs06/pImAiMv4n3GzpUdQKWFMJoB5x19hQVW6ymclN8HRqsT1YibZIOFFubxRUi2KIz8amamigJFKmnI7azwhd9K5ZOWfn40VEmtsivHpsorjUQEGgkU3Dqk93V7y797z1sNCbyS1yyMr4fK7qsqEaCrpMzjYdyuPPxun+DG1TwftNlOU31MCLPoyuw0wq6WXq43a4mf18N67vPo7CxNhUkpVHxhcjz/PGBzKRaU5jYhI397xbMUt4MyxXWvjT82hm5kl1OigDioK2qNiPC+DNIdKu+o5N/kg2VZliSzUdL7JhPqeGWdXPcyNNHWuVYfPdx65dIdJipqRi0kOotxRq0EXeIp6eV5KoNvoqmP3NHs9/vxp38NVtB00DAq8xYIQTVUyaJrHob5sGsKN98pM/dQOvBJbnmwqEqpVYzcZTUF+drCxEgJkAdzbby/kG3ZJe9OBYPZICrkIWZE3io+Xeu8b+VA5zyf9n3K1v5PHUpC9FYFKRvTOzMm0LKn2fg9M7dWZ6LZ4sPDXRZSuyt4o2UlGnDA66tvEsoyXn3d+G+2H2fTdsrvBnTe1NmidDt7n86kV7a1SvijyxYU5f2e7+UuayXva7pTI+NQMmTuHwviK+rImpTXXCm8FKxiFNIj+Mchtpk31qQxxRK+1smSaFou4wmwlxhiou4O3+t66fXb7vu41ab2pN9nRhQI8NMGXNuHhHUsOcUsRU0bWR5nNZoKavRXmvhWqNRNyF173zGqRDTevy+na32v4ui89tNifrDbJVhVc0x6QOBBUebws2rDxu7tkHwMOujUaDacbEsdf0kDDKhEVTg8ZA3mSkx3nfb3okffe77a2uoc01lXaLbdI1ePV+OU6INXox/7fd+m72bLhhFxb5l1tHtX56Qjn0XsK/NOHVGCUq//jQddezt/3lqut0A0Gf91n4HzUgFvWa3EgDrJwUhPy+597hP2cX7Kn/XSac7NQx7nOca4FRdFDLHdSFBlkBpQiVNPEBZL1hmUEItGGIIA4HiFE2URtYzXUCq4HXEE1pz9PV6oacVDZMvXlKIWoMYWW46HZi4yJPCehBZLpb6hznskQtZUjxFqpOPbJGqUEdYtK8DbyAHu0BzhhM3095n4xXPtG6CI/f1AGXpP6PswClVYrlDrPpKoKzQfzAeTthNuqtJgfuWr5JVZiArt7L9VQCwDnvzej0iKy1VSqq1NXiu0UXBCYk15ISuUH3kveQNSckjzt9XLjvJ/ddWtZc4gSUk5f4K7cG72cI5g8PbdyBa1RD8py5YbVVBKj5KjnRwHIMkQJ8igDcDZ+yDTkfbIooehtEn1UHZFclT1iZF6Wz3tTtt2SitpLJNqJuIxo9IFVjri17BzeycjGxN0BHVLv19Wfpn552KxF2+5u2D4HbYEmD27zs2k9j/c/HVc/uX1lEPlqEgkQS0PSDJtFQdopSQmjA8Hz3/r0yoTQ1DiqK9rgqNJnRMHYykrO82K3hiQBvV/e6+nq8eiuCdEb1l5xoCJsX09hDwbK1Esrl0qYpcjtoVihTtdhoq5/QNSdYrXYqrYfx5N4pWydl5IQCOGByY6GEFNbQGgu91PvP+r/947bbCa4crjiFolTckUpbrdvgu62QwT7xxscglUuGVa2b6tO+abT8voVFEkQjgUHYmCaAndi2CzZu+pvZ2W51PVyrT5aj88bH0gzCmaRxBexo6Dql4zqQ9rpRCWo8UaKoj2tuQk40YJ2SQILvoDu7T5e+CYETLVRYjXxCg0qtE6zmAY5eXNb91s9e95uh/bKBmo+f1yqSM2pUZEMD1LxJUu5B7frViSnVcqJHVZ/XojH1qSHqlIpWYfazM2mS5pGyMce8y23zRWIB19DQcNKK9fMOOd7PclGXtBXYTw+nVnFwVsuOXECDwikL489ezl5wZmzd3nwkNcgoT15UcLEpEwpNWXYtgfSseR9n4vGziuKcVfTmWDicVi07/gfSYv4Ghs0VL3jd6tvTMYVwWDp98BRLSKGI9yEQAJTk+L68Ph8/rGVXZ7VU4Zr+y8PCtHMebbODY9xtt+1G+3LMuKoSs1qsmHggBFRjuz3HCn4a+7b7evx0bpzLYn3kQoPAqYjC8rSKb1/ttInAmhOhNd4V8bvCgcY7jf5I3HhFw3r2ajXul0rgROq+sa6K0xUuTKwTwclg+6frlqY00ll3TMUqD50Rz0tWuImHBxHy9Pp2arolH+yRBvGGLiWhFQon6FZJVBVD36+7yWzk8XT8uNN9OC00cSUNTKfaUoFxDzAINVwN7fl8/LxpO4ji8xyLp20HVRgp/UK8v3ho9xfbIx0AflYdcEmcHnfRkDRLr/LbHD50u5vb9eyXXu9rc7YePx/b7rN4PccBimn3wsAztsTsPwzSxHl9p600zhyT8KoKTg8/yImGp9l/YA7l35Obs5yzxyRsY6KiIie/h6WRUP9xaAM8HzZ3SuBIDwAnlIveqPNjBTY0AmIKok0v+gdsQUZUnPNHERyb1ceT+j5wo+HpbESIT1/qpVwbfTYcP6vFZ+ez+EuyoWHpbDT+7rrZ2+5m/MBEVpC0c0duyEgYZkbt1Hnyyr+Jf4fq1LiUvuR2cZ1z6XjzRrnntQRAJsSJeyLD6eKP71nAbxI80kEnJwG6fTpP5+2Eo7MVCX53f89roqdiALXQlWMCsU48oP9z3k1F42yP6udvx5Vc5ysLqMfP+8bDol681brkeRHfeevNpy+EGISCN8cU9PjQeT2EcqxcNiZakeBPCPoji/CXUMJV337pg/P2WJSalrqg51BkaIPU2WpKwzO0Yfbj+DB80FE2590xgayMDFrJJUPTxEh1ary96oejpjR/ooahTpogDp1XK05sFEH+BABwQECy/BNNdMrFoEUNcrOB6exEjECwQPS81meYEntRmolCK8KTRFW3znpxY6MTQZ613qeLcVxrXcr5dKzMpbFQE1qysmHp7ESSL/r12DrsaAn+SA9Z3FMGRAXS5GMD0tmJFLXN7Kffxrudrv5IC59MONyx2OyUjw1I87cmyS+IGZCT9UjJ7poO1eO1NyQd9CSPfMwT/7LO0FED+xZFgjnhnDlwLkl9LEwoOrtmhHLsfzHcH87sXbAnJJr8op4DkocNRPMGWslllry3+kEtKLiTh5vusMYtrEsTds5eJdfL9P3zVTdcjZt1awz0JzTygX8STEKeEHT2Iry3+03f32kokiWEU+VR2UevsQR8bAg6e5GeHmI9m8BYiCfCaxYclXFkZAPQ7BbkFDLCyLsZUKjc8CgE0gmB5kSiZg1kY53Yp6Gw6e5RJKIOhWMV9JMrS1YjCQvDEx/1NFxR9LNVp5PQLpzqYPOlMWsoiW6C0TmIEM/6B0mE2u3GNIJwpIVP4uTOU9KAwhJ3Y6MeRr7l2c8PejeMNLaaExtq4SRpXYbsaFg8BxHid8slnAByiGEzzs9lh+0eWblSPAU+zQRZmJgmMM57kSOe/oAg/N36ZtNJLurisRaGKZAmLQaTC60qnYMGw/1JFIn+ZOktiic9e3Ss9068Ewk2BTrMiLsYTmTXYETSw0fHmu/EObXB1spxIb9CUJYfT1jfoEzW3gbysGUEWasJUKFhhxiy6vYH7qdT9cmT8CSEsCjdlLDVEjpeenQ2Tldbu3iqfvnAQIkgLEw3BsaWhcqtgK+71b1m8y6WEwk0PJm0KCO8bDyMYoTwQ//aDYdfSiYU6gmFhmiTnl8KNxsXW0FB6nKvxvE91Wfq459Qr1a1atQAkuKUFyChZTHhrPvImtz5evy3CCAdu8A0gfGs+E3Y6A53O9H6Bt4UNftlWHaKhtOp/mlN0WU97xQ2NvYlDYHyuxHOxt3NqgXw5E80oCUUWc87yUbX2Jc+IVGeC0kry7mwR/cfnR72if3UqjEk1SmbQPbFW3rOO2ky5/HA5n1LCNKpErbUKkeNJFnPP2UJIkGZpX3TU5c3S1lCayfxqcgBkRxteaOnnY7F9XbayXsXYMKr4Xr2dD+Ck3qw4lI+WUDLK7MW48hMPzFRzBAEfkNG9XSD1GZUKR7rYJky2+I1jrRTFiEgUry8ExU6RIJUT5SgZdVZzzldDlNOknOLg78fvAgfz+ZUh5R/RY84yccpH8nNBO+mKb9zYU+bJ5U7CUJU5mn4FEVszNPjhfOeN+C2UqC8/FgBM5ue5OV6rEkeTomIngy1XrBX/U0/JfXZn1DwB+ZJAMnlkItkTQjbDdyb4eZWaxI5nBBo9ZQSNH7wl8ZN7BPxybT+C3ZDUXT5WPnqVMlhec8oEydsoDURpNEP1LuG4eT16eT1VU24qOt3rKs3Ey4TCu1n50go9PUn0dNMVayqNX5yYcoktKbB/A/83z0QQTN4lmMHItVM6b00DcOzKD29XgtC+3/ttHtys558eHEnPHAqw6oHk9zJhOJLuytb+0flt/6QA8WfPB8PexAXXMoBxlfV302/Fwyx27SEuoRTIfjJiYoHLvUA5LUkoR74h+HmqpcTeldOoJRtMJ4uQLxwNQcYX4WLrf36UzmvpFMxNChcVX2pDhOM16rG4Xh92O80Hy+fCbJh8aqnOmTmhMW1MHF52y/73WZ22cmtACrLYz9gfUsmvGmAHAydALkWJw49tM92Wz1jcVO7Po/54Ymi+kKnInSsCTdz1nP+A4WLnqw4l5e0mxYdRcF2ejZf6GkjtzP1XJTAwaz2y9WOfiGfq/FUI20TRhJ/RM1swLaYhmp4w5HconnDC5pkFWmaOihcRVGvhGSTXolyrVMDi/zKX3jk2eX209xWPRFGaKAUiYA8542fQGnR/PxnZKT97MW4oUy1JdrVz4ShsNRbPTP0/C2updFQXKlR4RIc5f0C8sukzCkJhabeaqWDHGnQtGiS/n8Bv+UBJtx5AAA="
STATE = APP_DIR / "fantasy_edge_state.json"

def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii","ignore").decode().lower()
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b","",s)
    k = re.sub(r"[^a-z0-9]","",s)
    # V6.59 canonical aliases: Yahoo/club feeds sometimes shorten first names.
    # Keep ownership identity stable so an explicit team assignment always beats
    # a historical ROSTERED_UNKNOWN alias.
    aliases={
        "kenwalker":"kennethwalker",
        "kennethwalker":"kennethwalker",
        "kennygainwell":"kennethgainwell",
        "kennethgainwell":"kennethgainwell",
        "jakobilane":"jakobilane",
    }
    return aliases.get(k,k)

def load_state():
    default={
        "teams":12,"ppr":1.0,"pass_td":4,"faab":100,
        "my_team":[],"taken":[],"ownership":{},"team_names":{},"injury_overrides":{},
        "roster_slots":{"QB":1,"RB":2,"WR":2,"TE":1,"FLEX":2,"K":1,"DL":1,"DB":1,"BENCH":6},
        "mock":{"draft_slot":1,"rounds":17,"randomness":12},
        "idp":{"solo":1.5,"assist":0.75,"sack":4.0,"tfl":2.0,"qb_hit":0.0,
               "int":7.0,"pd":2.0,"ff":4.0,"fr":4.0,"def_td":12.0,"safety":8.0}
    }
    if STATE.exists():
        try:
            saved=json.loads(STATE.read_text())
            default.update({k:v for k,v in saved.items() if k not in ["idp","roster_slots","mock"]})
            default["idp"].update(saved.get("idp",{}))
            default["roster_slots"].update(saved.get("roster_slots",{}))
            default["mock"].update(saved.get("mock",{}))
        except: pass
    return default

def exact_roster_rounds(slots):
    """Total draft rounds implied by the exact roster template."""
    return int(sum(max(int(slots.get(p,0)),0) for p in ["QB","RB","WR","TE","FLEX","K","DL","DB","BENCH"]))

def _cloud_config():
    # Streamlit secrets can override these packaged publishable settings.
    try:
        url=str(st.secrets.get("SUPABASE_URL",_CLOUD_DEFAULT_URL)).rstrip("/")
        key=str(st.secrets.get("SUPABASE_PUBLISHABLE_KEY",_CLOUD_DEFAULT_KEY))
    except Exception:
        url=_CLOUD_DEFAULT_URL; key=_CLOUD_DEFAULT_KEY
    return url,key

def _cloud_headers():
    _,key=_cloud_config()
    h={"apikey":key,"Content-Type":"application/json"}
    # Legacy anon keys are JWTs and may be used as Bearer tokens.
    # Modern sb_publishable_* keys should be sent as apikey only.
    if key.startswith("eyJ"):
        h["Authorization"]=f"Bearer {key}"
    return h

def _cloud_probe():
    """Read the cloud row without mutating local or remote state."""
    url,_=_cloud_config()
    endpoint=f"{url}/rest/v1/fantasy_edge_state?league_key=eq.{CLOUD_LEAGUE_KEY}&select=state,updated_at"
    req=urllib.request.Request(endpoint,headers=_cloud_headers(),method="GET")
    with urllib.request.urlopen(req,timeout=5) as r:
        rows=json.loads(r.read().decode("utf-8"))
    if rows and isinstance(rows[0].get("state"),dict):
        return {"state":rows[0]["state"],"updated_at":rows[0].get("updated_at","")}
    return None

def _cloud_load():
    row=_cloud_probe()
    return row.get("state") if isinstance(row,dict) else None

def _v705_ownership_stats(s):
    own=(s or {}).get("ownership",{}) or {}
    if not isinstance(own,dict): own={}
    rostered=0; unknown=0; fa=0
    for entry in own.values():
        if not isinstance(entry,dict): continue
        owner=str(entry.get("owner","FA"))
        if owner=="FA": fa+=1
        elif owner=="ROSTERED_UNKNOWN":
            rostered+=1; unknown+=1
        else:
            rostered+=1
    return {"rostered":rostered,"unknown":unknown,"free_agents":fa,"ownership_entries":len(own)}

def _v705_state_is_suspicious(candidate,baseline):
    """Protect a complete local league from obviously incomplete/stale cloud payloads."""
    c=_v705_ownership_stats(candidate); b=_v705_ownership_stats(baseline)
    if b["rostered"]>=50 and c["rostered"]==0:
        return True,"Cloud ownership map is empty while the local league is populated."
    if b["rostered"]>=100 and c["rostered"] < b["rostered"]-12:
        return True,f"Cloud has {c['rostered']} rostered players vs {b['rostered']} locally."
    if c["unknown"] > b["unknown"]+10 and b["unknown"]<=5:
        return True,f"Cloud contains {c['unknown']} unknown-team assignments vs {b['unknown']} locally."
    return False,""

def _v705_write_sync_status(ok,mode,error="",cloud_updated_at=""):
    payload={
        "ok":bool(ok),"mode":str(mode),"error":str(error or ""),
        "cloud_updated_at":str(cloud_updated_at or ""),
        "checked_at":datetime.now(timezone.utc).isoformat()
    }
    try: _SYNC_STATUS_FILE.write_text(json.dumps(payload,indent=2))
    except Exception: pass
    st.session_state["_v657_cloud_ok"]=bool(ok)
    st.session_state["_v657_cloud_error"]=str(error or "")
    st.session_state["_v705_cloud_mode"]=str(mode)
    st.session_state["_v705_cloud_updated_at"]=str(cloud_updated_at or "")
    st.session_state["_v705_cloud_checked_at"]=payload["checked_at"]

def _v705_read_sync_status():
    try:
        if _SYNC_STATUS_FILE.exists():
            x=json.loads(_SYNC_STATUS_FILE.read_text())
            return x if isinstance(x,dict) else {}
    except Exception: pass
    return {}

def _cloud_save(s):
    """Write the current state to the shared league row.
    Update-first avoids ambiguous upsert behavior with RLS/PostgREST.
    """
    url,_=_cloud_config()
    headers=_cloud_headers()
    headers["Prefer"]="return=representation"

    # 1) Update the known row directly.
    patch_endpoint=f"{url}/rest/v1/fantasy_edge_state?league_key=eq.{CLOUD_LEAGUE_KEY}"
    patch_payload=json.dumps({"state":s,"updated_at":datetime.now(timezone.utc).isoformat()}).encode("utf-8")
    patch_req=urllib.request.Request(patch_endpoint,data=patch_payload,headers=headers,method="PATCH")
    with urllib.request.urlopen(patch_req,timeout=6) as r:
        body=r.read().decode("utf-8")
        if not (200 <= int(r.status) < 300):
            raise RuntimeError(f"Cloud PATCH failed HTTP {r.status}")
        rows=json.loads(body) if body.strip() else []
        if isinstance(rows,list) and len(rows)>0:
            return True

    # 2) If the row somehow does not exist, insert it.
    post_endpoint=f"{url}/rest/v1/fantasy_edge_state"
    post_payload=json.dumps({
        "league_key":CLOUD_LEAGUE_KEY,
        "state":s,
        "updated_at":datetime.now(timezone.utc).isoformat()
    }).encode("utf-8")
    post_req=urllib.request.Request(post_endpoint,data=post_payload,headers=headers,method="POST")
    with urllib.request.urlopen(post_req,timeout=6) as r:
        if not (200 <= int(r.status) < 300):
            raise RuntimeError(f"Cloud POST failed HTTP {r.status}")
    return True

def save_state(s):
    """Local-first save with verified cloud sync. A cloud failure can never erase the local state."""
    STATE.write_text(json.dumps(s,indent=2))
    try:
        _cloud_save(s)
        row=_cloud_probe()
        chk=row.get("state") if isinstance(row,dict) else None
        if not isinstance(chk,dict):
            raise RuntimeError("Cloud verification returned no state.")
        # Verify the ownership payload really survived the round trip.
        local_stats=_v705_ownership_stats(s); cloud_stats=_v705_ownership_stats(chk)
        if local_stats["rostered"]!=cloud_stats["rostered"] or local_stats["unknown"]!=cloud_stats["unknown"]:
            raise RuntimeError(f"Cloud verification mismatch: local {local_stats}, cloud {cloud_stats}")
        _v705_write_sync_status(True,"CONNECTED_VERIFIED","",row.get("updated_at","") if isinstance(row,dict) else "")
    except Exception as e:
        _v705_write_sync_status(False,"LOCAL_ONLY",repr(e),"")

def _owner_key(name):
    """Canonical ownership identity key; suffix variants are the same player."""
    s=str(name or "").strip().lower()
    s=s.replace("’","'").replace("`","'")
    s=re.sub(r"\b(jr|sr|ii|iii|iv|v)\.?\s*$","",s,flags=re.I).strip()
    s=re.sub(r"[^a-z0-9]","",s)
    aliases={
        "kenwalker":"kennethwalker",
        "kennethwalkeriii":"kennethwalker",
        "kennygainwell":"kennethgainwell",
        "kennethgainwell":"kennethgainwell",
    }
    return aliases.get(s,s)

def _ensure_ownership_state(s, names=None):
    # V6.75 collapse legacy suffix-specific ownership keys on every load.
    _legacy_own=s.get("ownership",{}) or {}
    if isinstance(_legacy_own,dict) and _legacy_own:
        _canon={}
        for _legacy_key,_entry in _legacy_own.items():
            if not isinstance(_entry,dict):
                continue
            _display=str(_entry.get("player","") or _legacy_key).strip()
            _key=_owner_key(_display)
            if not _key:
                continue
            _owner=str(_entry.get("owner","FREE AGENT"))
            _prev=_canon.get(_key)
            if _prev is None or (_prev.get("owner")=="FREE AGENT" and _owner!="FREE AGENT"):
                _canon[_key]={"player":_display,"owner":_owner}
        s["ownership"]=_canon

    if not isinstance(s.get("ownership"),dict): s["ownership"]={}
    if not isinstance(s.get("team_names"),dict): s["team_names"]={}
    for i in range(1,int(s.get("teams",12))+1):
        s["team_names"].setdefault(str(i),"My Team" if i==1 else f"Team {i}")
    own=s["ownership"]
    # Canonicalize any pre-V6.59 ownership keys and resolve collisions. An
    # explicit numbered team always wins over ROSTERED_UNKNOWN.
    reconciled={}
    for oldk,rec in list(own.items()):
        if not isinstance(rec,dict): continue
        player=str(rec.get("player",oldk)).strip()
        if not player: continue
        k=_owner_key(player)
        incoming={"player":player,"owner":str(rec.get("owner","ROSTERED_UNKNOWN"))}
        existing=reconciled.get(k)
        if existing is None or (existing.get("owner")=="ROSTERED_UNKNOWN" and incoming.get("owner")!="ROSTERED_UNKNOWN"):
            reconciled[k]=incoming
    own.clear(); own.update(reconciled)
    # Recover ownership from the persistent draft log too. This protects against
    # older versions that wrote a draft_log entry but did not immediately update
    # the ownership map.
    for entry in s.get("draft_log",[]) or []:
        if not isinstance(entry,dict):
            continue
        p=str(entry.get("player","")).strip()
        if not p:
            continue
        owner_kind=str(entry.get("owner","")).strip().lower()
        team_text=str(entry.get("team","")).strip()
        if owner_kind=="mine" or team_text.lower() in ("my team","griffin"):
            recovered_owner="1"
        else:
            # If the log contains a recognizable numbered team, preserve it;
            # otherwise drafted still means NOT a free agent.
            recovered_owner="ROSTERED_UNKNOWN"
            m=re.search(r"(?:team\s*)?(\d+)$",team_text.lower())
            if m and 1 <= int(m.group(1)) <= int(s.get("teams",12)):
                recovered_owner=str(int(m.group(1)))
        k=_owner_key(p)
        existing=own.get(k)
        if existing is None or (existing.get("owner")=="ROSTERED_UNKNOWN" and recovered_owner!="ROSTERED_UNKNOWN"):
            own[k]={"player":p,"owner":recovered_owner}

    for n in s.get("taken",[]) or []:
        if str(n).strip():
            own.setdefault(_owner_key(n),{"player":str(n).strip(),"owner":"ROSTERED_UNKNOWN"})
    for n in s.get("my_team",[]) or []:
        if str(n).strip():
            own[_owner_key(n)]={"player":str(n).strip(),"owner":"1"}
    if names:
        bykey={_owner_key(n):str(n) for n in names if str(n).strip()}
        for k,rec in own.items():
            if k in bykey and isinstance(rec,dict): rec["player"]=bykey[k]
    return s

def _player_owner(s,name):
    rec=(s.get("ownership") or {}).get(_owner_key(name))
    return rec.get("owner","FA") if isinstance(rec,dict) else "FA"

def _is_free_agent(s,name):
    """Return True only when all persisted ownership sources say free agent."""
    key=_owner_key(name)
    if _player_owner(s,name)!="FA":
        return False
    legacy_names=list(s.get("taken",[]) or [])+list(s.get("my_team",[]) or [])
    if key in {_owner_key(n) for n in legacy_names if str(n).strip()}:
        return False
    for entry in s.get("draft_log",[]) or []:
        if isinstance(entry,dict) and _owner_key(entry.get("player",""))==key:
            return False
    return True

def _sync_legacy_from_ownership(s):
    my=[]; taken=[]
    for rec in (s.get("ownership") or {}).values():
        if not isinstance(rec,dict): continue
        p=str(rec.get("player","")).strip(); o=str(rec.get("owner","FA"))
        if not p or o=="FA": continue
        taken.append(p)
        if o=="1": my.append(p)
    s["my_team"]=list(dict.fromkeys(my)); s["taken"]=list(dict.fromkeys(taken))
    return s

@st.cache_data(ttl=1800)
def sleeper_players():
    # Used only as a live NFL player directory, not as the fantasy-league source.
    r=requests.get("https://api.sleeper.app/v1/players/nfl",timeout=6)
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=86400, show_spinner="Updating NFL statistics...")
def nfl_history():
    try:
        import nflreadpy as nfl
        raw=nfl.load_player_stats([2023,2024,2025]).to_pandas()
        if "season_type" in raw:
            raw=raw[raw.season_type.eq("REG")]

        name="player_display_name" if "player_display_name" in raw else "player_name"
        if "position" not in raw:
            return pd.DataFrame()

        # Keep offensive + defensive positions.
        allowed=["QB","RB","WR","TE","DL","DE","DT","NT","EDGE","DB","CB","S","FS","SS"]
        raw=raw[raw.position.isin(allowed)].copy()
        raw["_g"]=1

        # Ensure all needed columns exist.
        offensive_cols=["passing_yards","passing_tds","interceptions","rushing_yards","rushing_tds",
                        "receptions","receiving_yards","receiving_tds","targets","carries"]
        defensive_cols=["def_tackles_solo","def_tackles_with_assist","def_sacks","def_tackles_for_loss",
                        "def_qb_hits","def_interceptions","def_pass_defended","def_fumbles_forced",
                        "def_fumble_recovery_opp","def_tds","def_safety"]
        for c in offensive_cols+defensive_cols:
            if c not in raw: raw[c]=0

        raw["fantasy_points_ppr"]=(
            raw.passing_yards.fillna(0)/25 + raw.passing_tds.fillna(0)*4
            - raw.interceptions.fillna(0)*2 + raw.rushing_yards.fillna(0)/10
            + raw.rushing_tds.fillna(0)*6 + raw.receptions.fillna(0)
            + raw.receiving_yards.fillna(0)/10 + raw.receiving_tds.fillna(0)*6
        )

        agg={"fantasy_points_ppr":"sum","_g":"sum"}
        for c in offensive_cols+defensive_cols:
            agg[c]="sum"

        x=raw.groupby(["season",name,"position"],dropna=False).agg(agg).reset_index().rename(columns={name:"player"})
        x["games"]=x["_g"].clip(lower=1)
        if x.games.median()<=2: x["games"]=17
        x["ppr_ppg"]=x.fantasy_points_ppr/x.games
        x["key"]=x.player.map(norm)
        x["position_group"]=x["position"].map(position_group)
        return x
    except Exception as e:
        pass  # V7.04: cached loaders must not mutate st.session_state
        return pd.DataFrame()

@st.cache_data(ttl=21600, show_spinner="Updating 2026 consensus rankings...")
def market_rankings(ppr):
    """Latest FantasyPros expert-consensus rankings via nflverse/DynastyProcess."""
    try:
        import nflreadpy as nfl
        try:
            raw = nfl.load_ff_rankings("draft").to_pandas()
        except TypeError:
            raw = nfl.load_ff_rankings().to_pandas()
        if raw.empty or "player" not in raw.columns or "ecr" not in raw.columns:
            return pd.DataFrame()
        raw = raw.copy()
        raw["ecr"] = pd.to_numeric(raw["ecr"], errors="coerce")
        raw = raw[raw.ecr.notna()]
        raw["key"] = raw.player.map(norm)
        raw["page"] = raw.get("page_type", pd.Series("", index=raw.index)).fillna("").astype(str).str.lower()
        raw["etype"] = raw.get("ecr_type", pd.Series("", index=raw.index)).fillna("").astype(str).str.lower()
        raw["pos_raw"] = raw.get("pos", pd.Series("", index=raw.index)).fillna("").astype(str)

        # Prefer overall redraft pages matching league reception scoring.
        score = pd.Series(0.0, index=raw.index)
        score += raw.page.str.contains("overall", regex=False).astype(float) * 5
        score += (~raw.page.str.contains("dynasty", regex=False)).astype(float) * 2
        score += (~raw.page.str.contains("week", regex=False)).astype(float) * 2
        if ppr == 1.0:
            score += (raw.page.str.contains("ppr", regex=False) & ~raw.page.str.contains("half", regex=False)).astype(float) * 5
        elif ppr == 0.5:
            score += (raw.page.str.contains("half", regex=False)).astype(float) * 5
        else:
            score += (~raw.page.str.contains("ppr", regex=False)).astype(float) * 3
        # IDP pages are useful for defenders, but not for offensive overall rank.
        is_idp_page = raw.page.str.contains("idp", regex=False)
        raw["page_score"] = score

        raw["consensus_pos"]=raw["pos_raw"].map(position_group)
        out=[]
        for (key,cpos),g in raw.groupby(["key","consensus_pos"], dropna=False):
            defender = cpos in ["DL","DB"]
            gg = g.copy()
            if defender and is_idp_page.loc[gg.index].any():
                gg = gg[is_idp_page.loc[gg.index]]
            elif not defender:
                non_idp = ~is_idp_page.loc[gg.index]
                if non_idp.any(): gg = gg[non_idp]
            mx = gg.page_score.max()
            gg = gg[gg.page_score.eq(mx)]
            row = gg.sort_values("ecr").iloc[0]
            out.append({"key":key,"consensus_pos":cpos,"consensus_rank":float(row.ecr),"consensus_page":row.page})
        return pd.DataFrame(out)
    except Exception as e:
        pass  # V7.04: cached loaders must not mutate st.session_state
        return pd.DataFrame()

def position_group(pos):
    if pos in ["DE","DT","NT","EDGE","DL"]: return "DL"
    if pos in ["CB","S","FS","SS","DB"]: return "DB"
    return pos

def canonical_position(raw_pos):
    p=str(raw_pos or "").upper().strip()
    aliases={"HB":"RB","FB":"RB","NT":"DL","DT":"DL","DE":"DL","EDGE":"DL","CB":"DB","S":"DB","FS":"DB","SS":"DB"}
    return aliases.get(p,p)

def validate_position(player, pos):
    """Canonicalize the source position only; never infer position from a player's name."""
    return canonical_position(pos)


# --- Fantasy Edge v9.1 production layer (v9.08 certified) ---
V9_BOARD = APP_DIR / "production_board.csv"
V9_CONFIG = APP_DIR / "engine_config.csv"

@st.cache_data
def load_v9_production():
    """Load the certified v9.1 production board and round-specific engine weights."""
    # V6.51: the authoritative production board is embedded directly in app.py.
    # This prevents Streamlit/Fork working-directory or stale-repository CSVs from
    # silently loading an older player pool. File fallback exists only if decode fails.
    try:
        _embedded_bytes = gzip.decompress(base64.b64decode(_V651_BOARD_GZ_B64.encode("ascii")))
        pb = pd.read_csv(io.BytesIO(_embedded_bytes))
    except Exception:
        if not V9_BOARD.exists():
            return pd.DataFrame(), {"default":(16.0,2.0,.2,.5), "rounds":{}}
        pb=pd.read_csv(V9_BOARD)
    # V6.19 cornerstone pool certification: never silently ship without current
    # first/second-round anchors. This protects dropdown + recommendation pool.
    _cornerstones=["CeeDee Lamb","Kenneth Walker III","Justin Jefferson","Saquon Barkley",
                   "Brock Bowers","Ashton Jeanty","Drake London","A.J. Brown","Nico Collins",
                   "DeVonta Smith","Bo Nix","Colston Loveland","Ladd McConkey","David Montgomery","Bhayshul Tuten","Jeremiyah Love","Jadarian Price","Carnell Tate","George Kittle","Harold Fannin Jr.","Dalton Kincaid","Isaiah Likely","KC Concepcion","Jayden Reed","Matthew Golden","Jayden Higgins","Kenyon Sadiq","DJ Moore","Luther Burden III"]
    _missing_cornerstones=[_p for _p in _cornerstones if _p not in set(pb["Player"].astype(str))]
    if _missing_cornerstones:
        raise RuntimeError("Production player pool missing cornerstone players: "+", ".join(_missing_cornerstones))

    # V6.23 broader top-100 offensive universe smoke test.
    _top100_smoke=[
        "DeVonta Smith","CeeDee Lamb","Kenneth Walker III","Justin Jefferson","Saquon Barkley",
        "Brock Bowers","Drake London","A.J. Brown","Nico Collins","Rashee Rice","Malik Nabers",
        "Chris Olave","Garrett Wilson","Tee Higgins","Jaylen Waddle","Terry McLaurin",
        "Bo Nix","Colston Loveland","Ladd McConkey","David Montgomery","Bhayshul Tuten","Jeremiyah Love","Jadarian Price","Carnell Tate","George Kittle","Harold Fannin Jr.","Dalton Kincaid","Isaiah Likely","KC Concepcion","Jayden Reed","Matthew Golden","Jayden Higgins","Kenyon Sadiq","DJ Moore","Luther Burden III"
    ]
    _missing_top100=[_p for _p in _top100_smoke if _p not in set(pb["Player"].astype(str))]
    if _missing_top100:
        raise RuntimeError("Top-100 offensive player pool incomplete: "+", ".join(_missing_top100))
    pb["key"]=pb["Player"].map(norm)
    # Backward-compatible v9.1 hotfix: derive Base_live_score from certified board fields if absent.
    if "Base_live_score" not in pb.columns:
        def _z9(s):
            s=pd.to_numeric(s,errors="coerce")
            sd=s.std(ddof=0)
            return (s-s.mean())/(sd if pd.notna(sd) and sd!=0 else 1.0)
        pb["Base_live_score"]=(0.55*_z9(pb["Draft_score"])
                               +0.30*_z9(pb["VORP"])
                               +0.15*_z9(-pd.to_numeric(pb["Market_pick"],errors="coerce")))
    cfg={"default":(16.0,2.0,.2,.5), "rounds":{}}
    if V9_CONFIG.exists():
        ec=pd.read_csv(V9_CONFIG)
        vals=dict(zip(ec["Field"].astype(str),ec["Value"].astype(str)))
        def _weights(v):
            try: return tuple(float(x.strip()) for x in str(v).strip("()").split(","))
            except: return None
        d=_weights(vals.get("Default_weights"))
        if d and len(d)==4: cfg["default"]=d
        for k,v in vals.items():
            m=re.fullmatch(r"Round_(\d+)_weights",k)
            w=_weights(v)
            if m and w and len(w)==4: cfg["rounds"][int(m.group(1))]=w
    return pb,cfg

def attach_v9_production(board):
    """Attach certified player signals without disturbing the rest of the dashboard."""
    pb,_=load_v9_production()
    if pb.empty: return board
    keep=pb[["key","Market_pick","VORP","Draft_score","Model_rank","Base_live_score"]].drop_duplicates("key")
    keep=keep.rename(columns={
        "Market_pick":"v9_market_pick","VORP":"v9_vorp","Draft_score":"v9_draft_score",
        "Model_rank":"v9_model_rank","Base_live_score":"v9_base_live_score"})
    return board.merge(keep,on="key",how="left")

def v9_live_rank(avail, round_no, current_pick, roster_counts):
    """Certified v9.08 translation used by the v9.1 live draft assistant."""
    pb,cfg=load_v9_production()
    x=avail.copy()
    if pb.empty or "v9_base_live_score" not in x:
        x["v9_live_score"]=_safe_num_series(x,"draft_score",0.0)
        return x
    # Frozen champion round/player and position priors reconstructed from production board rank/timing.
    # Player identity prior is represented by the certified static base score; round overrides control
    # the dynamic translation exactly as certified in v9.08.
    pw,posw,tw,nw=cfg["rounds"].get(int(round_no),cfg["default"])
    mp=pd.to_numeric(x["v9_market_pick"],errors="coerce").fillna(pd.to_numeric(x["market_pick"],errors="coerce"))
    delta=float(current_pick)-mp
    timing=np.where(delta>=0,np.minimum(delta/18.0,1.5),np.maximum(delta/24.0,-1.5))
    base=pd.to_numeric(x["v9_base_live_score"],errors="coerce")
    fallback=(pd.to_numeric(x["draft_score"],errors="coerce").rank(pct=True)-.5)*2
    base=base.fillna(fallback)
    # Use model-rank percentile as a stable player-prior proxy for players on the certified board.
    mr=pd.to_numeric(x["v9_model_rank"],errors="coerce")
    player_prior=(1-(mr-1)/max(len(pb)-1,1)).clip(0,1).fillna(0)
    # Position prior from the currently available certified board at this round.
    pos_counts=pb["Position"].value_counts(normalize=True).to_dict()
    position_prior=x["position"].map(pos_counts).fillna(0)
    need=[]
    caps={"QB":(1,2),"RB":(2,99),"WR":(2,99),"TE":(1,2),"K":(1,1),"DL":(1,1),"DB":(1,1)}
    for p in x["position"]:
        lo,hi=caps.get(p,(0,99)); cnt=int(roster_counts.get(p,0))
        need.append(1.0 if cnt<lo else 0.0)
    x["v9_live_score"]=base+pw*player_prior+posw*position_prior+tw*timing+nw*np.asarray(need)
    x["v9_market_pick_effective"]=mp
    return x


def _v944_add_idp_display_metrics(x):
    """Add position-relative IDP metrics without overwriting raw projection/VORP/model_rank."""
    y=x.copy()
    if "idp_impact_score" not in y.columns:
        y["idp_impact_score"]=np.nan
    if "idp_external_rank" not in y.columns:
        y["idp_external_rank"]=np.nan

    y["display_projection"]=pd.to_numeric(y.get("projection",np.nan),errors="coerce")
    y["display_vorp"]=pd.to_numeric(y.get("vorp",np.nan),errors="coerce")
    y["display_model_rank"]=pd.to_numeric(y.get("model_rank",np.nan),errors="coerce")

    mask=y["position"].astype(str).str.upper().isin(["DL","DB"])
    # For IDP, show the score/rank actually used by the IDP mechanism.
    y.loc[mask,"display_projection"]=pd.to_numeric(y.loc[mask,"idp_impact_score"],errors="coerce")
    y.loc[mask,"display_vorp"]=pd.to_numeric(y.loc[mask,"roster_opportunity_adj"],errors="coerce")
    y.loc[mask,"display_model_rank"]=pd.to_numeric(y.loc[mask,"idp_external_rank"],errors="coerce")
    return y

def _marginal_roster_multiplier(pos, counts, slots):
    """How much of a player's raw value is realistically usable on this roster."""
    pos=str(pos)
    have=int(counts.get(pos,0))

    if pos=="RB":
        # RB1/RB2 starters, RB3/RB4 useful FLEX/depth, RB5+ sharply diminished.
        return [1.00,1.00,0.88,0.72,0.48,0.28,0.16][min(have,6)]
    if pos=="WR":
        # WR1/WR2 starters; WR3-WR5 remain useful in 2-FLEX; WR6+ diminished.
        return [1.00,1.00,0.92,0.82,0.68,0.46,0.28][min(have,6)]
    if pos=="TE":
        return 1.00 if have<1 else 0.38 if have==1 else 0.15
    if pos=="QB":
        return 1.00 if have<1 else 0.34 if have==1 else 0.10
    if pos=="K":
        return 1.00 if have<1 else 0.0
    if pos in ("DL","DB"):
        # Required starter is full value. First/second impact backup still useful.
        return 1.00 if have<1 else 0.78 if have==1 else 0.55 if have==2 else 0.30
    return 1.0


def _add_marginal_roster_value(x, roster, slots):
    """Add usable VORP / marginal roster value without overwriting raw VORP."""
    y=x.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}

    raw_vorp=_safe_num_series(y,"vorp",0.0)
    raw_proj=_safe_num_series(y,"projection",0.0)

    mult=y["position"].map(lambda p:_marginal_roster_multiplier(p,counts,slots)).astype(float)
    y["roster_value_multiplier"]=mult
    y["usable_vorp"]=raw_vorp*mult

    # Projection contributes only modestly to marginal value; VORP is primary.
    y["marginal_roster_value"]=(
        y["usable_vorp"]*2.4 +
        np.maximum(raw_proj,0.0)*0.12*mult
    )

    # Late-bench startability/upside proxy: reward candidates with enough projection
    # and usable VORP to plausibly enter the lineup; discount pure roster-cloggers.
    proj_rank=y.groupby("position")["projection"].rank(pct=True,ascending=True).fillna(0.5)
    vorp_rank=y.groupby("position")["vorp"].rank(pct=True,ascending=True).fillna(0.5)
    y["bench_startability"]=np.clip(0.55*proj_rank+0.45*vorp_rank,0.0,1.0)
    y["marginal_roster_value"]*=np.where(
        y["position"].isin(["RB","WR"]) & (mult<0.60),
        0.65+0.35*y["bench_startability"],
        1.0
    )
    return y

def _portfolio_depth_penalty(pos, counts):
    """Penalty for redundant bench concentration; starters/FLEX remain largely untouched."""
    pos=str(pos); have=int(counts.get(pos,0))
    if pos=="RB":
        return 0.0 if have<=3 else 2.0 if have==4 else 8.0 if have==5 else 14.0
    if pos=="WR":
        return 0.0 if have<=4 else 5.0 if have==5 else 10.0
    if pos=="QB":
        return 0.0 if have==0 else 7.0
    if pos=="TE":
        return 0.0 if have==0 else 6.0
    if pos=="K":
        return 0.0 if have==0 else 1000.0
    return 0.0


def _add_cross_position_bench_value(x, roster, slots):
    """Compare each deep-bench candidate to the best other-position use of that bench slot."""
    y=x.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    if "marginal_roster_value" not in y.columns:
        y=_add_marginal_roster_value(y,roster,slots)

    y["portfolio_depth_penalty"]=y["position"].map(lambda p:_portfolio_depth_penalty(p,counts)).astype(float)
    y["portfolio_value"]=pd.to_numeric(y["marginal_roster_value"],errors="coerce").fillna(0.0)-y["portfolio_depth_penalty"]

    # Best alternative at another position = opportunity cost of this bench slot.
    best_by_pos=y.groupby("position")["portfolio_value"].max().to_dict()
    alt=[]
    for _,row in y.iterrows():
        others=[v for p,v in best_by_pos.items() if p!=row.position and pd.notna(v)]
        alt.append(max(others) if others else 0.0)
    y["best_other_position_value"]=alt
    y["value_over_next_roster_slot"]=y["portfolio_value"]-y["best_other_position_value"]
    return y


def _benchmark_candidate_prefilter(avail, current_pick, per_position=12, overall_market=55):
    """
    Lossless-for-practical-draft benchmark prefilter:
    retain the market front plus leaders at every position by projection, VORP,
    draft score, and IDP quality. The exact production scorer chooses from this set.
    """
    if avail is None or len(avail)==0:
        return avail
    x=avail.copy()
    keep=set()

    market=_safe_num_series(x,"market_pick",999.0)
    if "consensus_rank" in x.columns:
        market=pd.to_numeric(x["consensus_rank"],errors="coerce").fillna(market)
    keep.update(market.nsmallest(min(int(overall_market),len(x))).index)

    for p in x["position"].astype(str).unique():
        pm=x["position"].astype(str).eq(p)
        xp=x.loc[pm]
        if xp.empty:
            continue
        for col,ascending in [("projection",False),("vorp",False),("draft_score",False),
                              ("idp_impact_score",False),("idp_external_rank",True)]:
            if col not in xp.columns:
                continue
            vals=pd.to_numeric(xp[col],errors="coerce")
            vals=vals.sort_values(ascending=ascending,na_position="last")
            keep.update(vals.head(min(int(per_position),len(vals))).index)

    return x.loc[x.index.isin(keep)].copy()


def prepare_user_draft_candidates(avail, roster, round_no, current_pick, slot, teams, slots, randomness):
    """Single pre-ranking pipeline used by both Live Draft Mode and Mock Draft Lab."""
    x=avail.copy()

    # Same injury/availability policy in both modes.
    if "injury_severity" in x.columns:
        x=x[pd.to_numeric(x["injury_severity"],errors="coerce").fillna(0)<3].copy()

    # V6.55: never recommend an offensive player whose displayed projection is
    # only a missing/fallback bucket. They remain searchable in the full board.
    if "projection_available" in x.columns:
        _off=x["position"].astype(str).isin(["QB","RB","WR","TE","K"])
        _has=x["projection_available"].fillna(False).astype(bool)
        x=x[(~_off)|_has].copy()

    total_rounds=exact_roster_rounds(slots)
    x=draft_eligibility(x,roster,int(round_no),int(total_rounds),slots)
    if x.empty:
        return x, None

    # Same roster context columns in both modes.
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    x["_construction_bonus"]=0.0

    _rb=int(counts.get("RB",0))
    _wr=int(counts.get("WR",0))
    _te=int(counts.get("TE",0))
    _rnd=int(round_no)

    # WR/TE starter-shell pressure.
    if _wr<2:
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=7.0
    elif _wr==2:
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=3.0
    elif _wr==3:
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=1.0
    elif _wr>=4:
        # WR5+ is bench value, not a construction target.
        x.loc[x.position.eq("WR"),"_construction_bonus"]+=0.0

    if _te<1 and _rnd>=4:
        x.loc[x.position.eq("TE"),"_construction_bonus"]+=2.5

    # RB marginal utility: RB1/RB2 are starters, RB3 can be a FLEX,
    # but RB4 before the WR/TE shell is built is effectively premature depth.
    if _rb>=2 and _rnd<=6:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=3.0
    if _rb>=3 and _rnd<=7:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=8.0
    if _rb>=4:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=7.0

    # Once RB5 is already rostered, RB6 carries a strong diminishing-return penalty.
    # The corresponding impact-IDP bonus is applied later, AFTER IDP evidence/tier fields exist.
    if _rb>=5:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=28.0
        x.loc[x.position.eq("RB"),"rb6_depth_penalty"]=-28.0
    if _wr>=5:
        x.loc[x.position.eq("WR"),"_construction_bonus"]-=20.0
        x.loc[x.position.eq("WR"),"wr6_depth_penalty"]=-20.0

    if _rb>=6:
        x.loc[x.position.eq("RB"),"_construction_bonus"]-=5000.0
        x.loc[x.position.eq("RB"),"deep_skill_hard_cap"]=True
    if _wr>=6:
        x.loc[x.position.eq("WR"),"_construction_bonus"]-=5000.0
        x.loc[x.position.eq("WR"),"deep_skill_hard_cap"]=True

    _qb=int(counts.get("QB",0))
    if _qb>=2 and _te>=1:
        x.loc[x.position.eq("TE"),"_construction_bonus"]-=32.0
        x.loc[x.position.eq("TE"),"second_backup_penalty"]=-32.0
    if _te>=2 and _qb>=1:
        x.loc[x.position.eq("QB"),"_construction_bonus"]-=32.0
        x.loc[x.position.eq("QB"),"second_backup_penalty"]=-32.0

    # Hard early-shell guard: do not take RB4 in rounds 1-6 while a required WR/TE
    # starter is still missing, unless no viable starter-position alternatives exist.
    _starter_shell_missing=(_wr<2) or (_te<1)
    if _rnd<=6 and _rb>=3 and _starter_shell_missing:
        _alternatives=x[
            x.position.isin(["WR","TE"]) &
            (
                ((x.position=="WR") & (_wr<2)) |
                ((x.position=="TE") & (_te<1))
            )
        ]
        if len(_alternatives):
            _ap=pd.to_numeric(_alternatives.get("projection",np.nan),errors="coerce")
            _av=pd.to_numeric(_alternatives.get("vorp",np.nan),errors="coerce")
            _viable=(_ap.notna() & _av.notna() & (_ap>0))
            if _viable.any():
                x.loc[x.position.eq("RB"),"_construction_bonus"]-=1000.0
                x.loc[x.position.eq("RB"),"early_rb_surplus_blocked"]=True

    if "early_rb_surplus_blocked" not in x.columns:
        x["early_rb_surplus_blocked"]=False
    if "impact_idp_depth_bonus" not in x.columns:
        x["impact_idp_depth_bonus"]=0.0
    if "rb6_depth_penalty" not in x.columns:
        x["rb6_depth_penalty"]=0.0
    if "wr6_depth_penalty" not in x.columns:
        x["wr6_depth_penalty"]=0.0
    if "deep_skill_hard_cap" not in x.columns:
        x["deep_skill_hard_cap"]=False
    if "second_backup_penalty" not in x.columns:
        x["second_backup_penalty"]=0.0
    x["early_rb_surplus_blocked"]=x["early_rb_surplus_blocked"].fillna(False).astype(bool)

    # Surplus-depth discipline while required slots are still open.
    _min_req,_fixed_def,_flex_extra=_minimum_required_picks_remaining(counts,slots)
    if _min_req>0:
        if int(counts.get("QB",0))>=int(slots.get("QB",1)):
            x.loc[x.position.eq("QB"),"_construction_bonus"]-=22.0
        if int(counts.get("TE",0))>=int(slots.get("TE",1)):
            x.loc[x.position.eq("TE"),"_construction_bonus"]-=18.0

        # If one required IDP position is missing, a backup at the other IDP
        # position cannot crowd it out.
        if int(counts.get("DB",0))<int(slots.get("DB",1)) and int(counts.get("DL",0))>=int(slots.get("DL",1)):
            x.loc[x.position.eq("DL"),"_construction_bonus"]-=30.0
            x.loc[x.position.eq("DB"),"_construction_bonus"]+=12.0
        if int(counts.get("DL",0))<int(slots.get("DL",1)) and int(counts.get("DB",0))>=int(slots.get("DB",1)):
            x.loc[x.position.eq("DB"),"_construction_bonus"]-=30.0
            x.loc[x.position.eq("DL"),"_construction_bonus"]+=12.0

    x["roster_need"]=x.position.map(lambda p: roster_need_for_mock(roster,p,slots))
    _sim_mode=("_sim_precomputed_idp" in x.columns and x["_sim_precomputed_idp"].fillna(False).astype(bool).all())
    _delta_cap=18 if _sim_mode else 64
    x["roster_delta"]=_candidate_roster_delta_df(roster,x,slots,exact_cap=_delta_cap)

    # Fantasy Edge marginal roster value: raw VORP is not equally usable at RB6/WR6/QB2/etc.
    x=_add_marginal_roster_value(x,roster,slots)
    x=_add_cross_position_bench_value(x,roster,slots)

    next_pick=next_user_pick(int(current_pick),int(slot),int(teams),int(total_rounds))
    x,_local=v939_shared_candidate_rank(
        x,roster,int(round_no),int(current_pick),next_pick,slots,int(randomness)
    )
    return x,next_pick


def _safe_num_series(df, name, default=0.0):
    if name in df.columns:
        return pd.to_numeric(df[name], errors="coerce").fillna(float(default))
    return pd.Series(float(default), index=df.index, dtype=float)


def _position_depth_after_pick(roster, pos):
    counts = roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    counts = dict(counts)
    p = str(pos)
    counts[p] = int(counts.get(p, 0)) + 1
    return counts


def _starter_flex_improvement(pos, counts, slots):
    """Continuous lineup value; no preferred 4-RB/5-WR template."""
    p = str(pos)
    have = int(counts.get(p, 0))
    need = int(slots.get(p, 0))

    if have < need:
        return 8.0

    if p in ("RB", "WR", "TE"):
        skill_have = int(counts.get("RB", 0)) + int(counts.get("WR", 0)) + int(counts.get("TE", 0))
        skill_need = (
            int(slots.get("RB", 0)) + int(slots.get("WR", 0)) +
            int(slots.get("TE", 0)) + int(slots.get("FLEX", 0))
        )
        if skill_have < skill_need:
            return 5.0

    # Smooth marginal decline after starter/FLEX usefulness is satisfied.
    depth = max(have - need, 0)
    curves = {
        "RB": [2.8, 2.0, 1.2, 0.3, -1.5, -3.5, -5.5],
        "WR": [3.0, 2.3, 1.6, 0.8, -0.8, -2.6, -4.5],
        "TE": [1.2, -1.5, -3.5],
        "QB": [0.8, -2.0, -4.0],
        "DL": [0.8, -1.2, -4.0],
        "DB": [0.8, -1.2, -4.0],
        "K": [-100.0, -100.0],
    }
    vals = curves.get(p, [0.0])
    return float(vals[min(depth, len(vals)-1)])


def _market_survival_probability(market_pick, current_pick, next_pick):
    """
    Smooth probability that a player survives until next turn.
    < 0.2 = strong urgency, > 0.7 = likely wait.
    """
    span = max(float(next_pick) - float(current_pick), 1.0)
    margin = float(market_pick) - float(next_pick)
    # logistic centered around next_pick; 6-pick temperature keeps this smooth
    return float(1.0 / (1.0 + np.exp(-margin / 6.0)))


def _same_position_next_turn_value(x, idx, current_pick, next_pick):
    """Expected best same-position value at next turn."""
    pos = str(x.at[idx, "position"])
    pool = x[x["position"].astype(str).eq(pos)].drop(index=idx, errors="ignore").copy()
    if pool.empty:
        return 0.0, 12.0, 0.0

    evals = _safe_num_series(pool, "evaluation_score", 0.0)
    unified = _safe_num_series(pool, "unified_pick_score", 0.0)
    base = np.maximum(evals, unified)

    market = _safe_num_series(pool, "market_pick", np.nan)
    if "market_pick" not in pool.columns and "consensus_rank" in pool.columns:
        market = _safe_num_series(pool, "consensus_rank", float(next_pick)+20)
    market = market.fillna(float(next_pick)+20)

    surv = market.map(lambda mp: _market_survival_probability(mp, current_pick, next_pick))
    expected = base * surv

    if len(expected):
        j = expected.idxmax()
        next_val = float(expected.loc[j])
        raw_next = float(base.loc[j])
        best_surv = float(surv.loc[j])
    else:
        next_val = raw_next = best_surv = 0.0

    current_val = float(max(
        pd.to_numeric(pd.Series([x.at[idx, "evaluation_score"]]), errors="coerce").fillna(0).iloc[0],
        pd.to_numeric(pd.Series([x.at[idx, "unified_pick_score"]]), errors="coerce").fillna(0).iloc[0],
    ))
    loss = float(np.clip(current_val - next_val, 0.0, 14.0))
    return next_val, loss, best_surv


def _cross_position_opportunity_cost(x, idx):
    """
    Best competing use of the same roster slot across other positions.
    This is the key anti-template mechanism.
    """
    pos = str(x.at[idx, "position"])
    score = _safe_num_series(x, "unified_pick_score", 0.0)
    other = x["position"].astype(str).ne(pos)
    if not other.any():
        return 0.0
    best_other = float(score[other].max())
    mine = float(score.loc[idx])
    return float(np.clip(best_other - mine, -10.0, 14.0))


def _tier_cliff_value(x, candidate_idx):
    pos = str(x.at[candidate_idx, "position"])
    pool = x[x["position"].astype(str).eq(pos)].copy()
    if len(pool) < 2:
        return 0.0

    score = _safe_num_series(pool, "unified_pick_score", 0.0)
    pool = pool.assign(_tier_score=score).sort_values("_tier_score", ascending=False)
    loc = np.where(pool.index.to_numpy() == candidate_idx)[0]
    if len(loc) == 0:
        return 0.0
    i = int(loc[0])
    if i >= len(pool)-1:
        return 0.0
    cliff = float(pool.iloc[i]["_tier_score"] - pool.iloc[i+1]["_tier_score"])
    return float(np.clip(cliff, 0.0, 10.0))


def _future_roster_portfolio_value(pos, counts, slots):
    """
    Score the roster after the candidate is added.
    No fixed roster target; only saturation and flexibility.
    """
    after = dict(counts)
    p = str(pos)
    after[p] = int(after.get(p, 0)) + 1

    rb, wr = int(after.get("RB", 0)), int(after.get("WR", 0))
    qb, te = int(after.get("QB", 0)), int(after.get("TE", 0))
    dl, db = int(after.get("DL", 0)), int(after.get("DB", 0))
    idp = dl + db

    value = 0.0
    # Flexibility reward while still filling usable offensive depth.
    skill = rb + wr + te
    skill_required = int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+int(slots.get("FLEX",0))
    if skill <= skill_required + 2:
        value += 1.0

    # Smooth saturation penalties.
    if rb >= 5: value -= 1.3 * (rb - 4)
    if wr >= 6: value -= 1.1 * (wr - 5)
    if qb >= 2: value -= 1.8 * (qb - 1)
    if te >= 2: value -= 1.4 * (te - 1)

    # IDP: 2 is normal, 3 can be good, 4+ is poor for this 17-player format.
    if idp == 3: value += 0.4
    if idp >= 4: value -= 6.0 + 3.0 * (idp - 4)

    return float(value)


def _live_opportunity_optimizer(x, roster, slots, current_pick, next_pick, top_n=20):
    """
    Final Live/Mock optimizer:
      current player value
      + lineup improvement
      + tier cliff
      + next-turn replacement loss
      + future roster portfolio value
      - cross-position opportunity cost
      - reach risk
    """
    y = x.copy()
    if y.empty:
        return y

    counts = roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    base = _safe_num_series(y, "unified_pick_score", 0.0)

    y["opportunity_score"] = base.astype(float)
    for col in [
        "lineup_improvement_component","tier_cliff_component","replacement_loss_component",
        "next_turn_survival_component","cross_position_cost_component","future_roster_component",
        "reach_risk_component"
    ]:
        y[col] = 0.0

    market = _safe_num_series(y, "market_pick", float(next_pick)+20)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market = _safe_num_series(y, "consensus_rank", float(next_pick)+20)

    serious = y.nlargest(min(int(top_n), len(y)), "opportunity_score").index

    for idx in serious:
        p = str(y.at[idx, "position"])

        lineup = _starter_flex_improvement(p, counts, slots)
        cliff = _tier_cliff_value(y, idx)
        _, replacement_loss, replacement_survival = _same_position_next_turn_value(
            y, idx, current_pick, next_pick
        )
        cross_cost = _cross_position_opportunity_cost(y, idx)
        future = _future_roster_portfolio_value(p, counts, slots)

        surv = _market_survival_probability(float(market.loc[idx]), current_pick, next_pick)
        urgency = (1.0 - surv) * 5.5

        reach = max(float(market.loc[idx]) - float(current_pick), 0.0)
        reach_risk = min(reach, 48.0) * 0.10

        y.at[idx, "lineup_improvement_component"] = lineup
        y.at[idx, "tier_cliff_component"] = cliff
        y.at[idx, "replacement_loss_component"] = replacement_loss
        y.at[idx, "next_turn_survival_component"] = surv
        y.at[idx, "cross_position_cost_component"] = cross_cost
        y.at[idx, "future_roster_component"] = future
        y.at[idx, "reach_risk_component"] = reach_risk

        y.at[idx, "opportunity_score"] += (
            lineup +
            0.85 * cliff +
            1.20 * replacement_loss +
            urgency +
            future -
            0.85 * max(cross_cost, 0.0) -
            reach_risk
        )

    # Recommendation confidence and challenger gap.
    ranked = y["opportunity_score"].sort_values(ascending=False)
    gap = float(ranked.iloc[0] - ranked.iloc[1]) if len(ranked) >= 2 else 8.0
    y["recommendation_confidence"] = np.clip(50.0 + gap * 6.5, 50.0, 99.0)
    y["challenger_gap"] = gap

    return y



def _objective_player_shortlist(x, top_n=15):
    """
    Stage 1: player-only shortlist.
    Uses projection, VORP, market value, model quality, injury/role and IDP talent.
    No roster need, saturation or bench-shape logic is allowed here.
    """
    y=x.copy()
    if y.empty:
        return y

    proj=_safe_num_series(y,"projection",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    market=_safe_num_series(y,"market_pick",999.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",999.0)

    raw_model=_safe_num_series(y,"draft_score",0.0)
    injury=_safe_num_series(y,"injury_penalty",0.0)
    role=_safe_num_series(y,"role_score",0.0)

    pos=y["position"].astype(str)
    proj_pct=proj.groupby(pos).rank(pct=True,method="average")
    vorp_pct=vorp.groupby(pos).rank(pct=True,method="average")
    market_pct=1.0-market.rank(pct=True,method="average")
    model_pct=raw_model.rank(pct=True,method="average")
    role_pct=role.groupby(pos).rank(pct=True,method="average") if "role_score" in y.columns else pd.Series(0.5,index=y.index)

    y["player_shortlist_score"]=100.0*(
        0.34*proj_pct.fillna(0.5) +
        0.32*vorp_pct.fillna(0.5) +
        0.15*market_pct.fillna(0.5) +
        0.12*model_pct.fillna(0.5) +
        0.07*role_pct.fillna(0.5)
    ) - np.clip(injury,0,30)*1.2

    idp=pos.isin(["DL","DB"])
    if idp.any():
        impact=_safe_num_series(y,"idp_impact_score",0.0)
        tier=_safe_num_series(y,"idp_quality_tier",5.0)
        ext=_safe_num_series(y,"idp_external_rank",50.0)
        impact_pct=impact.groupby(pos).rank(pct=True,method="average")
        ext_pct=1.0-ext.groupby(pos).rank(pct=True,method="average")
        tier_support=np.clip(1.0-(tier-1.0)/4.0,0,1)
        idp_quality=100.0*(0.52*impact_pct.fillna(0.5)+0.28*tier_support+0.20*ext_pct.fillna(0.5))
        y.loc[idp,"player_shortlist_score"]=0.62*y.loc[idp,"player_shortlist_score"]+0.38*idp_quality[idp]

    keep=set(y.nlargest(min(int(top_n),len(y)),"player_shortlist_score").index.tolist())
    for p in pos.dropna().unique():
        pm=pos.eq(p)
        keep.update(y.loc[pm].nlargest(min(3,int(pm.sum())),"player_shortlist_score").index.tolist())

    y["stage1_shortlisted"]=y.index.isin(keep)
    return y


def _future_pick_value(pool, counts, slots, future_pick, prior_pick, excluded=None):
    """Expected best usable roster value at a future turn."""
    q=pool.drop(index=list(excluded or []),errors="ignore").copy()
    if q.empty:
        return 0.0, None

    market=_safe_num_series(q,"market_pick",float(future_pick)+20)
    if "market_pick" not in q.columns and "consensus_rank" in q.columns:
        market=_safe_num_series(q,"consensus_rank",float(future_pick)+20)

    base=_safe_num_series(q,"player_shortlist_score",50.0)
    survival=market.map(lambda mp:_market_survival_probability(mp,prior_pick,future_pick))

    lineup=np.asarray([
        _starter_flex_improvement(p,counts,slots)
        for p in q["position"].astype(str)
    ],dtype=float)
    future=np.asarray([
        _future_roster_portfolio_value(p,counts,slots)
        for p in q["position"].astype(str)
    ],dtype=float)

    expected=0.74*base + 2.2*lineup + 1.2*future
    expected=expected*survival.to_numpy(dtype=float)

    if not np.isfinite(expected).any():
        return 0.0,None
    i=int(np.nanargmax(expected))
    return float(expected[i]),q.index[i]


def _two_pick_rollout_value(x, idx, roster, slots, current_pick, next_pick):
    """
    Stage 2 rollout: estimate the portfolio after this pick plus the next two user turns.
    Lightweight enough for live use; only top contenders receive a rollout.
    """
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    p=str(x.at[idx,"position"])
    after=dict(counts)
    after[p]=int(after.get(p,0))+1

    gap=max(int(next_pick)-int(current_pick),1)
    next2=int(next_pick)+gap

    first,first_idx=_future_pick_value(
        x,after,slots,int(next_pick),int(current_pick),excluded=[idx]
    )
    after2=dict(after)
    excluded=[idx]
    if first_idx is not None:
        p2=str(x.at[first_idx,"position"])
        after2[p2]=int(after2.get(p2,0))+1
        excluded.append(first_idx)

    second,_=_future_pick_value(
        x,after2,slots,int(next2),int(next_pick),excluded=excluded
    )

    # Future picks are discounted; current selection remains authoritative.
    return float(0.34*first + 0.20*second)


def _room_run_pressure(x, current_pick, next_pick):
    """
    Adaptive draft-room pressure by position.
    If the available board is being depleted ahead of market expectation, urgency rises.
    """
    y=x.copy()
    pos=y["position"].astype(str)
    market=_safe_num_series(y,"market_pick",999.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",999.0)

    pressure=pd.Series(0.0,index=y.index,dtype=float)
    span=max(int(next_pick)-int(current_pick),1)

    for p in pos.dropna().unique():
        pm=pos.eq(p)
        if not pm.any():
            continue
        likely_before_next=((market[pm]>=float(current_pick)) & (market[pm]<float(next_pick))).sum()
        available_now=int(pm.sum())
        # More players likely to disappear before next turn => more urgency.
        pr=float(np.clip(likely_before_next/max(min(available_now,8),1),0,1))*4.5
        pressure.loc[pm]=pr
    return pressure


def _candidate_stability(y, finalists, trials=24):
    """
    Perturb projection/VORP/market slightly. Stability is how often the same candidate wins.
    Deterministic seed from candidate count keeps rerenders stable.
    """
    if len(finalists)==0:
        return pd.Series(0.0,index=y.index)
    rng=np.random.default_rng(7000+len(y))
    base=_safe_num_series(y,"final_pick_value",-1e9)
    proj=_safe_num_series(y,"projection",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    market=_safe_num_series(y,"market_pick",999.0)
    wins={idx:0 for idx in finalists}

    for _ in range(int(trials)):
        perturb=(
            rng.normal(0,0.55,len(y)) +
            rng.normal(0,0.10,len(y))*proj.to_numpy(float) +
            rng.normal(0,0.18,len(y))*vorp.to_numpy(float) -
            rng.normal(0,0.015,len(y))*market.to_numpy(float)
        )
        vals=base.to_numpy(float)+perturb
        mask=np.array([idx in finalists for idx in y.index],dtype=bool)
        vals=np.where(mask,vals,-1e12)
        win_idx=y.index[int(np.nanargmax(vals))]
        if win_idx in wins:
            wins[win_idx]+=1

    out=pd.Series(0.0,index=y.index,dtype=float)
    for idx,n in wins.items():
        out.loc[idx]=n/max(int(trials),1)
    return out


def _two_stage_live_optimizer(x, roster, slots, current_pick, next_pick):
    """
    Player Value -> Candidate Shortlist -> Strategic Opportunity -> 2-pick Rollout
    -> Challenger Check -> FINAL PICK.
    """
    y=_objective_player_shortlist(x,top_n=15)
    if y.empty:
        return y

    # Stage 2 opportunity logic is only run on shortlisted players.
    strategic=_live_opportunity_optimizer(
        y[y["stage1_shortlisted"]].copy(),
        roster,slots,current_pick,next_pick,top_n=20
    )

    y["opportunity_score"]=-1e9
    y["rollout_value"]=0.0
    y["final_pick_value"]=-1e9
    y["recommendation_confidence"]=50.0
    y["challenger_gap"]=0.0

    for c in [
        "lineup_improvement_component","tier_cliff_component","replacement_loss_component",
        "next_turn_survival_component","cross_position_cost_component","future_roster_component",
        "reach_risk_component"
    ]:
        if c not in y.columns:
            y[c]=0.0
        if c in strategic.columns:
            y.loc[strategic.index,c]=strategic[c]

    y.loc[strategic.index,"opportunity_score"]=strategic["opportunity_score"]

    # Draft-room adaptation enters only at Stage 2.
    room_pressure=_room_run_pressure(y,current_pick,next_pick)
    y["room_run_pressure_component"]=room_pressure

    # Only the top five strategy candidates need the expensive rollout.
    finalists=strategic.nlargest(min(5,len(strategic)),"opportunity_score").index
    for idx in finalists:
        rv=_two_pick_rollout_value(y,idx,roster,slots,current_pick,next_pick)
        y.at[idx,"rollout_value"]=rv
        y.at[idx,"final_pick_value"]=(
            float(y.at[idx,"opportunity_score"])+rv+
            float(room_pressure.loc[idx])
        )

    # Non-finalists retain opportunity score but cannot beat finalists by missing rollout.
    other=strategic.index.difference(finalists)
    y.loc[other,"final_pick_value"]=y.loc[other,"opportunity_score"]

    ranked=y.loc[strategic.index,"final_pick_value"].sort_values(ascending=False)
    if len(ranked)>=2:
        gap=float(ranked.iloc[0]-ranked.iloc[1])
    else:
        gap=8.0
    # Candidate stability test: recommendations that flip under small data perturbations
    # should display lower confidence.
    stability=_candidate_stability(y,list(finalists),trials=24)
    y["candidate_stability"]=stability
    leader_stability=float(stability.loc[ranked.index[0]]) if len(ranked) else 0.0

    conf=float(np.clip(42.0+gap*4.8+leader_stability*35.0,45.0,99.0))
    y.loc[strategic.index,"recommendation_confidence"]=conf
    y.loc[strategic.index,"challenger_gap"]=gap

    # Best same-position and cross-position challenger values for auditability.
    leader=ranked.index[0] if len(ranked) else None
    y["best_same_position_challenger"]=np.nan
    y["best_cross_position_challenger"]=np.nan
    if leader is not None:
        lp=str(y.at[leader,"position"])
        same=strategic[strategic["position"].astype(str).eq(lp)].drop(index=leader,errors="ignore")
        cross=strategic[strategic["position"].astype(str).ne(lp)]
        same_v=float(y.loc[same.index,"final_pick_value"].max()) if len(same) else np.nan
        cross_v=float(y.loc[cross.index,"final_pick_value"].max()) if len(cross) else np.nan
        y.loc[strategic.index,"best_same_position_challenger"]=same_v
        y.loc[strategic.index,"best_cross_position_challenger"]=cross_v

    return y



def _base_player_value_engine(x):
    """One normalized player-value authority, independent of roster shape."""
    y=x.copy()
    pos=y["position"].astype(str)
    proj=_safe_num_series(y,"projection",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    market=_safe_num_series(y,"market_pick",999.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",999.0)
    model=_safe_num_series(y,"draft_score",0.0)
    injury=_safe_num_series(y,"injury_penalty",0.0)

    proj_pct=proj.groupby(pos).rank(pct=True,method="average")
    vorp_pct=vorp.groupby(pos).rank(pct=True,method="average")
    market_pct=1.0-market.rank(pct=True,method="average")
    model_pct=model.rank(pct=True,method="average")

    # Projection/VORP are the primary player-quality authority.
    base=100.0*(0.40*proj_pct.fillna(.5)+0.42*vorp_pct.fillna(.5)+
                0.10*market_pct.fillna(.5)+0.08*model_pct.fillna(.5))

    # Absolute VORP anchor prevents a mediocre player from becoming a top choice
    # solely because he ranks well inside a weak positional pool.
    _abs_vorp=np.clip((vorp+2.0)/14.0,0.0,1.0)
    y["absolute_vorp_anchor"]=(_abs_vorp-0.50)*10.0
    base+=y["absolute_vorp_anchor"]
    base-=np.clip(injury,0,30)*1.25

    # IDP is position-relative: impact/tier/external rank supplement projection/VORP.
    idp=pos.isin(["DL","DB"])
    if idp.any():
        impact=_safe_num_series(y,"idp_impact_score",0.0)
        tier=_safe_num_series(y,"idp_quality_tier",5.0)
        ext=_safe_num_series(y,"idp_external_rank",50.0)
        impact_pct=impact.groupby(pos).rank(pct=True,method="average")
        ext_pct=1.0-ext.groupby(pos).rank(pct=True,method="average")
        tier_pct=np.clip(1.0-(tier-1.0)/4.0,0,1)
        idp_rel=100.0*(.48*impact_pct.fillna(.5)+.30*tier_pct+.22*ext_pct.fillna(.5))
        base.loc[idp]=.58*base.loc[idp]+.42*idp_rel.loc[idp]

    y["base_player_value"]=base
    return y


def _marginal_slot_value(pos, counts, slots):
    """Value of consuming the next roster slot; no target roster counts."""
    p=str(pos); have=int(counts.get(p,0)); req=int(slots.get(p,0))
    if have < req:
        return 9.0
    if p in ("RB","WR","TE"):
        skill=sum(int(counts.get(q,0)) for q in ("RB","WR","TE"))
        starter_skill=int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+int(slots.get("FLEX",0))
        if skill < starter_skill:
            return 5.5

    # Smooth diminishing utility only; not a prescribed roster template.
    depth=max(have-req,0)
    curve={
        # V6.8: RB5/WR5 remain legal, but their marginal utility must beat
        # genuine cross-position alternatives instead of receiving an automatic
        # positive depth bump. This is a soft value curve, not a roster target.
        "RB":[3.0,2.1,0.25,-1.4,-3.0,-4.8,-6.5],
        "WR":[3.2,2.4,0.45,-1.2,-2.8,-4.5,-6.2],
        "TE":[1.4,-1.2,-3.2],
        "QB":[1.0,-1.8,-3.8],
        "DL":[1.0,-1.0,-3.8],
        "DB":[1.0,-1.0,-3.8],
        "K":[-100.0,-100.0],
    }.get(p,[0.0])
    return float(curve[min(depth,len(curve)-1)])


def _survival_wait_cost(y, idx, current_pick, next_pick):
    """(1-P(survive)) × positional replacement drop."""
    p=str(y.at[idx,"position"])
    market=_safe_num_series(y,"market_pick",float(next_pick)+20)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",float(next_pick)+20)

    survive=_market_survival_probability(float(market.loc[idx]),current_pick,next_pick)
    pool=y[y["position"].astype(str).eq(p)].drop(index=idx,errors="ignore")
    mine=float(y.at[idx,"base_player_value"])
    repl=float(pool["base_player_value"].max()) if len(pool) else max(mine-12.0,0.0)
    drop=max(mine-repl,0.0)
    return float((1.0-survive)*drop), float(survive)


def _room_position_pressure(y,current_pick,next_pick):
    """Live board depletion proxy, calculated only from the current available board."""
    pos=y["position"].astype(str)
    market=_safe_num_series(y,"market_pick",float(next_pick)+20)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",float(next_pick)+20)
    out=pd.Series(0.0,index=y.index,dtype=float)
    for p in pos.unique():
        pm=pos.eq(p)
        soon=((market[pm]>=float(current_pick)) & (market[pm]<float(next_pick))).sum()
        depth=min(int(pm.sum()),10)
        out.loc[pm]=float(np.clip(soon/max(depth,1),0,1))*4.0
    return out


def _single_authority_strategy(y,roster,slots,round_no,current_pick,next_pick):
    """All roster/market strategy enters here, after base player value."""
    z=_base_player_value_engine(y)
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    room=_room_position_pressure(z,current_pick,next_pick)

    z["marginal_slot_value"]=0.0
    z["wait_cost"]=0.0
    z["survival_probability"]=0.0
    z["room_pressure"]=room
    z["strategic_pick_value"]=-1e9
    _cross_slot=np.clip(_safe_num_series(z,"value_over_next_roster_slot",0.0),-8.0,8.0)
    z["cross_slot_value"]=_cross_slot
    _market_raw=_safe_num_series(z,"market_pick",float(current_pick)+12.0)
    _model_market=pd.to_numeric(z["model_rank"],errors="coerce").fillna(_market_raw) if "model_rank" in z.columns else _market_raw.copy()
    _offense=~z["position"].astype(str).isin(["DL","DB","K"])
    _market=_market_raw.copy()
    _market.loc[_offense]=0.90*_market_raw.loc[_offense]+0.10*_model_market.loc[_offense]
    _reach_ahead=np.maximum(_market-float(current_pick)-6.0,0.0)
    _reach_cost=np.minimum(_reach_ahead,45.0)*0.58
    z["strategic_reach_cost"]=_reach_cost
    _ropp=_safe_num_series(z,"roster_opportunity_adj",0.0)
    _late_factor=0.0 if int(round_no)<=10 else min(2.0,0.35*(int(round_no)-10))
    _late_negative_cost=np.maximum(-_ropp-1.0,0.0)*(1.2+_late_factor)
    z["late_roster_opp_cost"]=_late_negative_cost

    # Prospective Draft-Value economics: reward players available at/after market
    # and charge for reaches. This mirrors the benchmark's realized value economics
    # so the optimizer improves the metric rather than learning about it afterward.
    _market_delta=float(current_pick)-_market
    _market_value_component=pd.Series(
        np.where(
            _market_delta>=0.0,
            np.minimum(_market_delta,30.0)*0.28,
            np.maximum(_market_delta,-28.0)*0.68
        ),
        index=z.index,dtype=float
    )
    z["prospective_market_value"]=_market_value_component

    # Direct opportunity-loss estimate. Negative roster opportunity and being
    # inferior to another-position bench use are charged before rollout.
    _cross_loss=np.maximum(-_cross_slot,0.0)
    _opp_loss=np.maximum(-_ropp,0.0)
    _prospective_opp_cost=1.15*_opp_loss + 0.85*_cross_loss
    z["prospective_opportunity_cost"]=_prospective_opp_cost

    # Explicit player-quality anchor used by FINAL PICK.
    _qvorp=_safe_num_series(z,"vorp",0.0).rank(pct=True,method="average")
    _qproj=_safe_num_series(z,"projection",0.0).groupby(z["position"].astype(str)).rank(pct=True,method="average")
    _quality_anchor=10.0*(0.68*_qvorp.fillna(.5)+0.32*_qproj.fillna(.5)-0.50)
    z["final_quality_anchor"]=_quality_anchor

    # Preserve the roster-construction work produced by prepare_user_draft_candidates.
    _construction_context=np.clip(_safe_num_series(z,"_construction_bonus",0.0),-30.0,18.0)
    z["final_construction_context"]=_construction_context

    # V6.8 adaptive portfolio regret. This is deliberately soft: it never blocks
    # a position. It simply makes the next redundant bench slot pay for the
    # opportunity it consumes, allowing a truly superior RB5/WR5/QB2/TE2 to win.
    def _portfolio_regret_for_pos(_p):
        _p=str(_p); _have=int(counts.get(_p,0))
        if _p in ("RB","WR"):
            _other="WR" if _p=="RB" else "RB"
            if _have < 4:
                return 0.0
            _pen=2.25 + 1.65*max(_have-4,0)
            if int(counts.get(_other,0)) <= 3:
                _pen += 1.25
            return float(_pen)
        if _p=="QB" and _have>=1:
            return 2.2 if int(round_no)<=11 else 1.0
        if _p=="TE" and _have>=1:
            return 2.0 if int(round_no)<=11 else 0.9
        if _p in ("DL","DB") and (int(counts.get("DL",0))+int(counts.get("DB",0)))>=2:
            return 1.0
        return 0.0
    z["portfolio_regret_cost"]=z["position"].map(_portfolio_regret_for_pos).astype(float)

    # Candidate pool: best overall plus best at every position.
    keep=set(z.nlargest(min(15,len(z)),"base_player_value").index)
    for p in z["position"].astype(str).unique():
        pm=z["position"].astype(str).eq(p)
        keep.update(z.loc[pm].nlargest(min(3,int(pm.sum())),"base_player_value").index)
    z["single_authority_shortlist"]=z.index.isin(keep)

    for idx in keep:
        p=str(z.at[idx,"position"])
        marginal=_marginal_slot_value(p,counts,slots)
        wait,survive=_survival_wait_cost(z,idx,current_pick,next_pick)

        # IDP extras receive no special bonus. Required DL/DB receive ordinary starter value.
        idp_total=int(counts.get("DL",0))+int(counts.get("DB",0))
        idp_pen=0.0
        if p in ("DL","DB") and idp_total>=3:
            idp_pen=100.0  # roster-size guard only

        z.at[idx,"marginal_slot_value"]=marginal
        z.at[idx,"wait_cost"]=wait
        z.at[idx,"survival_probability"]=survive
        z.at[idx,"strategic_pick_value"]=(
            float(z.at[idx,"base_player_value"])+
            2.0*marginal+
            1.35*wait+
            float(room.loc[idx])+
            1.70*float(_cross_slot.loc[idx])+
            1.15*float(_quality_anchor.loc[idx])+
            0.45*float(_construction_context.loc[idx])+
            float(_market_value_component.loc[idx])-
            float(_reach_cost.loc[idx])-
            float(_late_negative_cost.loc[idx])-
            float(_prospective_opp_cost.loc[idx])-
            float(z.at[idx,"portfolio_regret_cost"])-
            idp_pen
        )
    return z


def _branch_future_value(y,counts,slots,from_pick,to_pick,excluded,rng):
    """One lightweight stochastic future-board branch; vectorized for benchmark speed."""
    q=y.drop(index=list(excluded),errors="ignore")
    if q.empty:
        return 0.0,None

    market=_safe_num_series(q,"market_pick",float(to_pick)+20).to_numpy(dtype=float)
    if "market_pick" not in q.columns and "consensus_rank" in q.columns:
        market=_safe_num_series(q,"consensus_rank",float(to_pick)+20).to_numpy(dtype=float)
    base=_safe_num_series(q,"base_player_value",0.0).to_numpy(dtype=float)

    # Exact same logistic survival equation as _market_survival_probability, vectorized.
    margin=market-float(to_pick)
    probs=1.0/(1.0+np.exp(-margin/6.0))
    alive=rng.random(len(q)) < probs
    if not alive.any():
        alive[int(np.nanargmax(probs))]=True

    positions=q["position"].astype(str).to_numpy()
    unique_pos=np.unique(positions)
    marginal_map={p:2.0*_marginal_slot_value(p,counts,slots) for p in unique_pos}
    marginal=np.fromiter((marginal_map[p] for p in positions),dtype=float,count=len(positions))

    utility=base+marginal
    utility=np.where(alive,utility,-1e9)
    j=int(np.nanargmax(utility))
    return float(utility[j]),q.index[j]



def _multi_branch_rollout(y,idx,roster,slots,current_pick,next_pick,branches=10):
    """10 plausible board continuations through the next two user turns."""
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    p=str(y.at[idx,"position"])
    counts=dict(counts); counts[p]=int(counts.get(p,0))+1
    gap=max(int(next_pick)-int(current_pick),1)
    next2=int(next_pick)+gap
    rng=np.random.default_rng(9000+int(current_pick)*17+int(idx)%997)
    vals=[]
    for _ in range(int(branches)):
        v1,j1=_branch_future_value(y,counts,slots,current_pick,next_pick,[idx],rng)
        c2=dict(counts); ex=[idx]
        if j1 is not None:
            p2=str(y.at[j1,"position"]); c2[p2]=int(c2.get(p2,0))+1; ex.append(j1)
        v2,_=_branch_future_value(y,c2,slots,next_pick,next2,ex,rng)
        vals.append(.34*v1+.20*v2)
    return float(np.mean(vals)) if vals else 0.0


def _v610_take_now_wait_score(y, idx, current_pick, next_pick):
    """Expected advantage of taking a player now instead of waiting one turn.

    Positive = take-now urgency. Negative = value is likely replaceable/waitable.
    Uses market survival plus same-position replacement value, so this is a
    forward-looking decision term rather than a generic reach penalty.
    """
    if next_pick is None or int(next_pick) <= int(current_pick):
        return 0.0
    # V6.11 snake-turn correctness: when our next selection is immediately
    # adjacent, no opponent can take the player between our two picks. Do not
    # manufacture take-now urgency from stale market ADP in that zero-opponent gap.
    if int(next_pick)-int(current_pick) <= 1:
        return 0.0
    market=_safe_num_series(y,"market_pick",float(next_pick)+20.0)
    if "market_pick" not in y.columns and "consensus_rank" in y.columns:
        market=_safe_num_series(y,"consensus_rank",float(next_pick)+20.0)
    survive=_market_survival_probability(float(market.loc[idx]),current_pick,next_pick)
    mine=float(y.at[idx,"base_player_value"]) if "base_player_value" in y.columns else float(_safe_num_series(y,"unified_pick_score",0.0).loc[idx])
    pool=y[y["position"].astype(str).eq(str(y.at[idx,"position"]))].drop(index=idx,errors="ignore")
    if len(pool):
        pv=_safe_num_series(pool,"base_player_value",0.0)
        repl=float(pv.max())
    else:
        repl=max(mine-10.0,0.0)
    replacement_drop=max(mine-repl,0.0)
    # If likely gone, lock in the unique value. If likely to survive, waiting has value.
    urgency=(1.0-survive)*(1.6+0.85*replacement_drop)
    wait_credit=survive*min(max(float(market.loc[idx])-float(current_pick),0.0),30.0)*0.055
    # Onesie positions are especially costly to reach on when the market projects
    # survival to our next turn; preserve capital for RB/WR/FLEX value instead.
    p=str(y.at[idx,"position"])
    onesie_wait=0.0
    if p in ("QB","TE") and float(market.loc[idx]) >= float(next_pick)-2.0:
        onesie_wait=2.4*survive
    return float(np.clip(urgency-wait_credit-onesie_wait,-4.0,8.0))


def _v610_dynamic_bench_competition(y, idx, roster, slots):
    """Make every optional bench slot compete across positions on usable value."""
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    p=str(y.at[idx,"position"])
    have=int(counts.get(p,0)); need=int(slots.get(p,0))
    # Required starters are handled by construction/lineup logic, not bench competition.
    is_optional=have>=need
    if p in ("RB","WR","TE"):
        skill_have=sum(int(counts.get(q,0)) for q in ("RB","WR","TE"))
        skill_need=sum(int(slots.get(q,0)) for q in ("RB","WR","TE"))+int(slots.get("FLEX",0))
        if skill_have < skill_need:
            is_optional=False
    if not is_optional:
        return 0.0

    mrv=_safe_num_series(y,"marginal_roster_value",0.0)
    cross=_safe_num_series(y,"cross_position_bench_value",0.0)
    vorp=_safe_num_series(y,"vorp",0.0)
    mine=0.58*float(mrv.loc[idx])+0.27*float(cross.loc[idx])+0.15*float(vorp.loc[idx])
    optional=[]
    for j in y.index:
        q=str(y.at[j,"position"]); qhave=int(counts.get(q,0)); qneed=int(slots.get(q,0))
        qopt=qhave>=qneed
        if q in ("RB","WR","TE"):
            sh=sum(int(counts.get(k,0)) for k in ("RB","WR","TE"))
            sn=sum(int(slots.get(k,0)) for k in ("RB","WR","TE"))+int(slots.get("FLEX",0))
            if sh < sn: qopt=False
        if qopt:
            optional.append(0.58*float(mrv.loc[j])+0.27*float(cross.loc[j])+0.15*float(vorp.loc[j]))
    best=max(optional) if optional else mine
    gap=mine-best
    # Reward the best optional use; punish redundant depth that loses clearly.
    return float(np.clip(0.75*gap,-6.0,3.0))


def _v610_roster_regret_audit(roster, slots):
    """Post-draft harmful-decision audit used by certification/champion scoring."""
    if roster is None or len(roster)==0:
        return {"harmful_regret_count":99,"major_reach_count":99,"early_backup_count":99,"starter_vorp":0.0,"bench_upside":0.0}
    r=roster.copy()
    for c in ["vorp","projection","consensus_rank","mock_pick","marginal_roster_value"]:
        if c not in r.columns: r[c]=np.nan
        r[c]=pd.to_numeric(r[c],errors="coerce")
    reaches=(r["consensus_rank"]-r["mock_pick"]).fillna(0.0)
    raw_major=int((reaches>24).sum())
    if "avoidable_reach" in r.columns:
        avoid=r["avoidable_reach"].fillna(False).astype(bool)
    else:
        avoid=pd.Series(True,index=r.index,dtype=bool)
    major=int(((reaches>24) & avoid).sum())
    harmful=int(((reaches>18) & avoid & (r["vorp"].fillna(0)<2.0)).sum())
    early_backup=0
    for p in ("QB","TE"):
        q=r[r.position.astype(str).eq(p)].sort_values("mock_pick")
        if len(q)>=2 and float(q.iloc[1]["mock_pick"])<120:
            early_backup+=1; harmful+=1
    req={"QB":int(slots.get("QB",1)),"RB":int(slots.get("RB",2)),"WR":int(slots.get("WR",2)),"TE":int(slots.get("TE",1)),"K":int(slots.get("K",1)),"DL":int(slots.get("DL",1)),"DB":int(slots.get("DB",1))}
    used=set(); starter_vorp=0.0
    for p,n in req.items():
        if n<=0: continue
        idx=r[r.position.astype(str).eq(p)]["vorp"].fillna(0).nlargest(n).index
        used.update(idx.tolist()); starter_vorp+=float(r.loc[idx,"vorp"].fillna(0).sum())
    flex_pool=r.loc[~r.index.isin(used) & r.position.astype(str).isin(["RB","WR","TE"]),"vorp"].fillna(0)
    flex_n=int(slots.get("FLEX",0)); flex_idx=flex_pool.nlargest(flex_n).index
    used.update(flex_idx.tolist()); starter_vorp+=float(r.loc[flex_idx,"vorp"].fillna(0).sum())
    bench=r.loc[~r.index.isin(used)].copy()
    bench_upside=float(np.clip(bench["vorp"].fillna(0).clip(-2,10).sum(),-10,60))
    return {"harmful_regret_count":int(harmful),"major_reach_count":int(major),"raw_major_reach_count":int(raw_major),"early_backup_count":int(early_backup),"starter_vorp":float(starter_vorp),"bench_upside":bench_upside}


def _v610_champion_score(result):
    """Multi-objective promotion score. Legality/construction are non-negotiable."""
    if not bool(result.get("legal_roster",False)) or float(result.get("construction",0))<99.999:
        return -1000.0
    return float(
        0.28*float(result.get("model_edge",0))+
        0.25*float(result.get("draft_value",0))+
        0.20*float(result.get("positional_advantage",0))+
        0.12*float(result.get("grade",0))+
        0.08*min(float(result.get("starter_vorp",0)),70.0)+
        0.03*min(float(result.get("bench_upside",0)),30.0)-
        1.10*float(result.get("opportunity_penalty",0))-
        1.75*float(result.get("harmful_regret_count",0))-
        0.75*float(result.get("major_reach_count",0))
    )


def _single_authority_final(y,roster,slots,round_no,current_pick,next_pick,compute_stability=True,rollout_branches=10):
    """
    Single source of truth:
    Base Player Value -> Strategic Pick Value -> 10-branch rollout
    -> regret/challenger test -> FINAL PICK.
    """
    z=_single_authority_strategy(y,roster,slots,int(round_no),current_pick,next_pick)
    contenders=z[z["single_authority_shortlist"]].nlargest(min(5,int(z["single_authority_shortlist"].sum())),"strategic_pick_value").index

    z["rollout_value"]=0.0
    z["final_pick_value"]=z["strategic_pick_value"]
    for idx in contenders:
        rv=_multi_branch_rollout(z,idx,roster,slots,current_pick,next_pick,branches=max(int(rollout_branches),1))
        z.at[idx,"rollout_value"]=rv
        z.at[idx,"final_pick_value"]=float(z.at[idx,"strategic_pick_value"])+rv

    # V6.8 Tested Regret Winner: regret now changes FINAL PICK. For each serious
    # candidate, measure the value package sacrificed at another position when
    # that challenger is unlikely to survive the turn. This prevents rollout/timing
    # from selecting redundant depth unless the player advantage really clears it.
    z["challenger_regret_cost"]=0.0
    z["take_now_wait_component"]=0.0
    z["dynamic_bench_component"]=0.0
    _short=z["single_authority_shortlist"].fillna(False).astype(bool)
    _mrv=_safe_num_series(z,"marginal_roster_value",0.0)
    _vorp=_safe_num_series(z,"vorp",0.0)
    _ropp2=_safe_num_series(z,"roster_opportunity_adj",0.0)
    _market2=_safe_num_series(z,"market_pick",float(current_pick)+20.0)
    for _idx in list(z.index[_short]):
        _p=str(z.at[_idx,"position"])
        _alts=_short & (~z["position"].astype(str).eq(_p))
        if not bool(_alts.any()):
            continue
        _alt_idx=z.loc[_alts,"strategic_pick_value"].idxmax()
        _mrv_gap=max(float(_mrv.loc[_alt_idx]-_mrv.loc[_idx]),0.0)
        _vorp_gap=max(float(_vorp.loc[_alt_idx]-_vorp.loc[_idx]),0.0)
        _ropp_gap=max(float(_ropp2.loc[_alt_idx]-_ropp2.loc[_idx]),0.0)
        _alt_survive=_market_survival_probability(float(_market2.loc[_alt_idx]),current_pick,next_pick)
        _urgency=0.35+0.65*(1.0-float(_alt_survive))
        _depth_mult=1.0
        _have=int((roster.position.astype(str)==_p).sum()) if roster is not None and len(roster) else 0
        if _p in ("RB","WR") and _have>=4: _depth_mult=1.35
        elif _p in ("QB","TE") and _have>=1: _depth_mult=1.15
        _cost=_depth_mult*_urgency*(0.70*_mrv_gap+0.45*_vorp_gap+0.30*_ropp_gap)
        z.at[_idx,"challenger_regret_cost"]=float(np.clip(_cost,0.0,12.0))
        z.at[_idx,"take_now_wait_component"]=_v610_take_now_wait_score(z,_idx,current_pick,next_pick)
        z.at[_idx,"dynamic_bench_component"]=_v610_dynamic_bench_competition(z,_idx,roster,slots)
    z.loc[_short,"final_pick_value"]=(
        z.loc[_short,"final_pick_value"]
        - z.loc[_short,"challenger_regret_cost"]
        + 0.35*z.loc[_short,"take_now_wait_component"]
        + 0.30*z.loc[_short,"dynamic_bench_component"]
    )

    ranked=z.loc[_short,"final_pick_value"].sort_values(ascending=False)
    gap=float(ranked.iloc[0]-ranked.iloc[1]) if len(ranked)>=2 else 10.0
    z["expected_regret"]=0.0
    if len(ranked):
        best=float(ranked.iloc[0])
        z.loc[ranked.index,"expected_regret"]=best-z.loc[ranked.index,"final_pick_value"]

    # Stability uses the same final authority.
    finalists=list(contenders)
    if compute_stability:
        stability=_candidate_stability(z,finalists,trials=24)
        lead_stab=float(stability.loc[ranked.index[0]]) if len(ranked) else 0.0
    else:
        # Stability only changes displayed confidence; it never changes FINAL PICK.
        stability=pd.Series(0.0,index=z.index,dtype=float)
        lead_stab=0.0
    z["candidate_stability"]=stability
    z["challenger_gap"]=gap
    z["recommendation_confidence"]=float(np.clip(42.0+4.5*gap+35.0*lead_stab,45,99))
    return z


def v939_shared_candidate_rank(avail, roster, round_no, current_pick, next_pick, slots, randomness=6):
    """One authoritative scoring pipeline for Draft Mode and Mock Draft Lab."""
    # On the user's final draft turn there is no future snake pick. Normalize None
    # to the current pick so wait/survival urgency becomes effectively neutral.
    if next_pick is None:
        next_pick=int(current_pick)
    else:
        next_pick=int(next_pick)
    x=avail.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}

    # V6.32 QB draft-day role guard. The production board contains historical/depth
    # quarterbacks that are useful for data continuity but must never surface as
    # DRAFT NOW / VALUE FALLER candidates in a 1-QB live draft when they do not own
    # a viable 2026 starting role. Keep the block centralized here so Draft Mode and
    # Mock Draft Lab use identical eligibility.
    _qb_nonstarter_block = {
        "Carson Wentz", "Michael Pratt", "Derek Carr", "Diego Pavia"
    }
    if "player" in x.columns:
        _player_name = x["player"].astype(str)
    elif "Player" in x.columns:
        _player_name = x["Player"].astype(str)
    else:
        _player_name = pd.Series("", index=x.index, dtype=str)
    _qb_role_block = x["position"].astype(str).str.upper().eq("QB") & _player_name.isin(_qb_nonstarter_block)
    x["qb_role_blocked"] = _qb_role_block
    if _qb_role_block.any():
        x = x.loc[~_qb_role_block].copy()

    # Compute IDP evidence first so all downstream gates can use it.
    _idp_mask=x["position"].astype(str).str.upper().isin(["DL","DB"])
    _reuse_sim_idp=(
        "_sim_precomputed_idp" in x.columns and
        bool(x["_sim_precomputed_idp"].fillna(False).astype(bool).all()) and
        all(_c in x.columns for _c in ["idp_impact_score","idp_external_rank","idp_eligible","idp_quality_tier"])
    )
    if not _reuse_sim_idp:
        x["idp_impact_score"]=np.nan
        x["idp_external_rank"]=np.nan
        x["idp_eligible"]=pd.Series(pd.NA,index=x.index,dtype="boolean")
    else:
        x["idp_eligible"]=x["idp_eligible"].fillna(False).astype("boolean")
    x["roster_completion_blocked"]=False
    x["extra_idp_blocked"]=False
    x["deep_offense_blocked_for_idp"]=False
    x["bench_diversification_blocked"]=False
    x["extra_idp_opportunity_loss"]=False

    if _idp_mask.any() and not _reuse_sim_idp:
        _idp_rows=x.loc[_idp_mask]
        _idp_scores=_idp_rows.apply(_v935_idp_impact_score,axis=1)
        x.loc[_idp_mask,"idp_impact_score"]=[v[0] for v in _idp_scores]
        x.loc[_idp_mask,"idp_eligible"]=pd.Series(
            [bool(v[1]) for v in _idp_scores],
            index=_idp_rows.index,dtype="boolean"
        )
        x.loc[_idp_mask,"idp_external_rank"]=_idp_rows.apply(_v936_external_idp_rank,axis=1)
    _overlay=x.get("id",pd.Series("",index=x.index)).astype(str).str.match(r"^v9\d+:")
    _er=pd.to_numeric(x["idp_external_rank"],errors="coerce")
    _fb=((_overlay & x["position"].eq("DL") & _er.notna() & (_er<=15)) |
         (_overlay & x["position"].eq("DB") & _er.notna() & (_er<=20)))
    x.loc[_fb,"idp_eligible"]=pd.Series(True,index=x.index[_fb],dtype="boolean")
    _floor=np.where(x["position"].eq("DL"),np.maximum(5.5,16.0-_er*0.60),np.maximum(5.0,14.0-_er*0.42))
    _cur=pd.to_numeric(x["idp_impact_score"],errors="coerce").fillna(0)
    x.loc[_fb,"idp_impact_score"]=np.maximum(_cur[_fb],_floor[_fb])
    x["idp_consensus_fallback"]=_fb
    if not _reuse_sim_idp:
        x["idp_quality_tier"]=np.nan
        x["idp_quality_evidence"]=np.nan
        if _idp_mask.any():
            _q=x.loc[_idp_mask].apply(_v941_idp_quality,axis=1)
            x.loc[_idp_mask,"idp_quality_tier"]=[v[0] for v in _q]
            x.loc[_idp_mask,"idp_quality_evidence"]=[v[1] for v in _q]
    elif "idp_quality_evidence" not in x.columns:
        x["idp_quality_evidence"]=np.nan

    # IDP quality is computed above. Extra-IDP timing is decided only by the
    # two-stage opportunity/rollout optimizer below; no pre-score IDP bonus is applied here.
    x=v9_live_rank(x,int(round_no),int(current_pick),counts)
    x["evaluation_score"]=pd.to_numeric(x["v9_live_score"],errors="coerce").fillna(-1e9)
    x["evaluation_score"]-=_safe_num_series(x,"injury_penalty",0.0)

    # Stage-1 player evaluation stays roster-agnostic.
    # Roster construction, saturation and cross-position opportunity are handled
    # only by the final two-stage optimizer below.

    x=roster_opportunity_adjustment(x,roster,int(round_no),int(current_pick),slots)
    # Do not inject roster opportunity into Stage-1 player quality.
    x=apply_v931_idp_opportunity_gate(x,roster,int(round_no))
    x=apply_v932_exact_league_construction(x,roster,int(round_no),exact_roster_rounds(slots),slots)

    # Hard roster-completion authority. This is the final safety layer used by
    # both Live Draft and Mock Draft Lab.
    _rounds=exact_roster_rounds(slots)
    _counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _min_now,_,_=_minimum_required_picks_remaining(_counts,slots)
    _picks_left=int(_rounds)-int(round_no)+1

    if _min_now>0:
        _after_min=[]
        for _p in x["position"].astype(str):
            _after=dict(_counts)
            _after[_p]=int(_after.get(_p,0))+1
            _m,_,_=_minimum_required_picks_remaining(_after,slots)
            _after_min.append(_m)
        x["minimum_required_after_pick"]=_after_min

        _remaining_after=max(int(_rounds)-int(round_no),0)
        _strands=pd.to_numeric(x["minimum_required_after_pick"],errors="coerce")>_remaining_after
        x.loc[_strands,"evaluation_score"]-=5000.0
        x.loc[_strands,"roster_completion_blocked"]=True

        if _picks_left<=_min_now:
            _does_not_reduce=pd.to_numeric(x["minimum_required_after_pick"],errors="coerce")>=_min_now
            x.loc[_does_not_reduce,"evaluation_score"]-=5000.0
            x.loc[_does_not_reduce,"roster_completion_blocked"]=True

    # Deep-offense vs impact-IDP competition is handled continuously by the
    # final opportunity optimizer; no non-legality hard block is applied here.

    # V6.9 cost-aware same-position Pareto dominance.
    # Quality authority must not hard-block a cheaper market option merely because
    # a slightly better player exists 15-25 picks later. A player is hard-dominated
    # only when the superior same-position alternative is also similarly priced.
    _proj_all=pd.to_numeric(x.get("projection",np.nan),errors="coerce")
    _vorp_all=pd.to_numeric(x.get("vorp",np.nan),errors="coerce")
    _market_all=_safe_num_series(x,"market_pick",999.0)
    if "market_pick" not in x.columns and "consensus_rank" in x.columns:
        _market_all=_safe_num_series(x,"consensus_rank",999.0)
    x["same_pos_dominated"]=False
    x["same_pos_soft_dominated"]=False
    x["same_pos_quality_gap"]=0.0

    for _p in ("QB","RB","WR","TE"):
        _idxp=list(x.index[x["position"].eq(_p)])
        if len(_idxp)<2:
            continue
        for _i in _idxp:
            _pi=float(_proj_all.loc[_i]) if pd.notna(_proj_all.loc[_i]) else -np.inf
            _vi=float(_vorp_all.loc[_i]) if pd.notna(_vorp_all.loc[_i]) else -np.inf
            _mi=float(_market_all.loc[_i]) if pd.notna(_market_all.loc[_i]) else 999.0
            _others=[j for j in _idxp if j!=_i]
            _dom=[]
            for _j in _others:
                _pj=float(_proj_all.loc[_j]) if pd.notna(_proj_all.loc[_j]) else -np.inf
                _vj=float(_vorp_all.loc[_j]) if pd.notna(_vorp_all.loc[_j]) else -np.inf
                if (_pj>=_pi and _vj>=_vi and ((_pj-_pi)>=0.20 or (_vj-_vi)>=0.20)):
                    _dom.append(_j)
            if not _dom:
                continue
            _best=max(_dom,key=lambda j:(float(_vorp_all.loc[j])+0.4*float(_proj_all.loc[j])))
            _gap=max(0.0,float(_proj_all.loc[_best])-_pi)*1.5 + max(0.0,float(_vorp_all.loc[_best])-_vi)*2.5
            x.at[_i,"same_pos_quality_gap"]=_gap
            _dm=float(_market_all.loc[_best]) if pd.notna(_market_all.loc[_best]) else 999.0
            if _dm <= _mi + 8.0:
                x.at[_i,"same_pos_dominated"]=True
                x.at[_i,"evaluation_score"]-=min(40.0,8.0+2.0*_gap)
            else:
                # Dominator is materially more expensive/later: keep the cheaper
                # player eligible and apply only a bounded quality tax.
                x.at[_i,"same_pos_soft_dominated"]=True
                x.at[_i,"evaluation_score"]-=min(6.0,1.25*_gap)

    # v9.50 RB quality authority: among available RBs, projection and VORP carry
    # more weight than ADP/faller noise. This is rank-relative and player-agnostic.
    _rb=x["position"].eq("RB")
    if _rb.any():
        _rp=pd.to_numeric(x.loc[_rb,"projection"],errors="coerce")
        _rv=pd.to_numeric(x.loc[_rb,"vorp"],errors="coerce")
        _proj_pct=_rp.rank(pct=True,method="average")
        _vorp_pct=_rv.rank(pct=True,method="average")
        _rb_quality=(0.42*_proj_pct + 0.58*_vorp_pct)
        x.loc[_rb,"rb_quality_score"]=_rb_quality*100.0
        x.loc[_rb,"evaluation_score"]+=(_rb_quality-0.50)*16.0

    # Negative roster opportunity is an authoritative cost.
    _ropp=_safe_num_series(x,"roster_opportunity_adj",0.0)
    _neg_ropp=_ropp < -3.0
    x.loc[_neg_ropp,"evaluation_score"]-=np.minimum(24.0,(-_ropp[_neg_ropp]-3.0)*1.35)

    # A strongly negative bench-IDP fit is never a FINAL PICK after required DL/DB are filled.
    _idp_counts2=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _both_idp_filled=(
        int(_idp_counts2.get("DL",0))>=int(slots.get("DL",1)) and
        int(_idp_counts2.get("DB",0))>=int(slots.get("DB",1))
    )
    if _both_idp_filled:
        _bad_idp_fit=x["position"].isin(["DL","DB"]) & (_ropp<-5.0)
        x.loc[_bad_idp_fit,"evaluation_score"]-=5000.0

    # v9.45 quality authority: roster/market urgency decides WHEN, not WHO.
    _off=~x["position"].isin(["DL","DB","K"])
    _vorp=pd.to_numeric(x.get("vorp",np.nan),errors="coerce")
    _mr=pd.to_numeric(x.get("model_rank",np.nan),errors="coerce")
    _profile=x.get("profile",pd.Series("",index=x.index)).astype(str).str.lower()
    _bad_off=_off & ((_vorp < 0) | _profile.str.contains("decline",na=False))
    x.loc[_bad_off,"evaluation_score"]-=14.0 + np.minimum(10.0,(-_vorp[_bad_off]).clip(lower=0)*3.0)
    x.loc[_off & (_mr>1000),"evaluation_score"]-=8.0

    # IDP talent is independent of roster urgency: quality controls WHICH DL/DB.
    for _p in ("DL","DB"):
        _pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if _pm.any():
            _impact=pd.to_numeric(x.loc[_pm,"idp_impact_score"],errors="coerce").fillna(-99)
            _ext=pd.to_numeric(x.loc[_pm,"idp_external_rank"],errors="coerce")
            _tier=pd.to_numeric(x.loc[_pm,"idp_quality_tier"],errors="coerce").fillna(5)
            _talent=(0.75*_impact) + (6-_tier)*2.5 + np.where(_ext.notna(),np.maximum(0,25-_ext)*0.18,0)
            x.loc[_pm,"evaluation_score"] += _talent
            x.loc[_pm,"idp_talent_score"] = _talent
            _ordered=x.loc[_pm].copy()
            _ordered["_talent_tmp"]=_talent
            _ordered=_ordered.sort_values(["idp_quality_tier","_talent_tmp"],ascending=[True,False])
            if len(_ordered):
                _best_idx=_ordered.index[0]
                _best_tier=float(pd.to_numeric(pd.Series([_ordered.iloc[0]["idp_quality_tier"]]),errors="coerce").fillna(5).iloc[0])
                _second_tier=float(pd.to_numeric(pd.Series([_ordered.iloc[1]["idp_quality_tier"]]),errors="coerce").fillna(5).iloc[0]) if len(_ordered)>1 else 5.0
                if _best_tier<=2 and _second_tier>_best_tier:
                    x.at[_best_idx,"evaluation_score"]+=5.0
                    x.at[_best_idx,"idp_dropoff_bonus"]=5.0

    # v9.47 strict IDP positional authority.
    # Roster urgency can decide WHEN to draft DL/DB, but cannot make a lower-quality
    # defender beat an available elite defender at the same position.
    x["idp_quality_blocked"]=False
    x["elite_idp_bonus"]=0.0
    x["elite_idp_quota_blocked"]=False
    for _p in ("DL","DB"):
        _pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if not _pm.any():
            continue

        _tiers=pd.to_numeric(x.loc[_pm,"idp_quality_tier"],errors="coerce").fillna(5.0)
        _exts=pd.to_numeric(x.loc[_pm,"idp_external_rank"],errors="coerce")
        _talents=pd.to_numeric(x.loc[_pm,"idp_talent_score"],errors="coerce").fillna(-99.0)

        _best_tier=float(_tiers.min())
        _valid_ext=_exts.dropna()
        _best_ext=float(_valid_ext.min()) if len(_valid_ext) else np.nan
        _best_talent=float(_talents.max())

        # If Tier 1/2 exists, Tier 3+ becomes context only.
        if _best_tier<=2:
            _tier_all=pd.to_numeric(x["idp_quality_tier"],errors="coerce").fillna(5.0)
            _blocked=_pm & (_tier_all>=3)
            x.loc[_blocked,"evaluation_score"]-=1000.0
            x.loc[_blocked,"idp_quality_blocked"]=True

        # Strong elite-rank authority.
        _elite_cut=6 if _p=="DL" else 8
        _rank_gap=5 if _p=="DL" else 7
        if pd.notna(_best_ext) and _best_ext<=_elite_cut:
            _all_ext=pd.to_numeric(x["idp_external_rank"],errors="coerce")
            _all_talent=_safe_num_series(x,"idp_talent_score",-99.0)
            _lower=_pm & _all_ext.notna() & (_all_ext>=_best_ext+_rank_gap) & (_all_talent<_best_talent+6.0)
            x.loc[_lower,"evaluation_score"]-=1000.0
            x.loc[_lower,"idp_quality_blocked"]=True

    # v9.49 elite-IDP quota.
    # Goal: finish the draft with at least ONE elite defender, while still letting
    # value/timing decide whether that elite player is DL or DB.
    _roster_elite=False
    if roster is not None and len(roster):
        _r=roster.copy()
        if "idp_quality_tier" in _r.columns:
            _rt=pd.to_numeric(_r["idp_quality_tier"],errors="coerce")
            _rp=_r["position"].astype(str).str.upper().isin(["DL","DB"])
            _roster_elite=bool((_rp & (_rt<=2)).any())

    _elite_avail=(
        x["position"].isin(["DL","DB"]) &
        x["idp_eligible"].fillna(False).astype(bool) &
        (pd.to_numeric(x["idp_quality_tier"],errors="coerce")<=2)
    )

    if (not _roster_elite) and _elite_avail.any():
        # Escalating value pressure: pursue elite IDP before the final two rounds.
        _elite_bonus=0.0
        if int(round_no)>=10: _elite_bonus=4.0
        if int(round_no)>=12: _elite_bonus=9.0
        if int(round_no)>=14: _elite_bonus=18.0
        x.loc[_elite_avail,"evaluation_score"]+=_elite_bonus
        x.loc[_elite_avail,"elite_idp_bonus"]=_elite_bonus

        # By Round 15, if an elite defender still exists, do not spend the pick on
        # a non-required bench luxury. Required K/TE/DL/DB completion remains exempt.
        if int(round_no)>=15:
            _counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
            _required_open={
                "TE":int(_counts.get("TE",0))<int(slots.get("TE",0)),
                "K":int(_counts.get("K",0))<int(slots.get("K",0)),
                "DL":int(_counts.get("DL",0))<int(slots.get("DL",0)),
                "DB":int(_counts.get("DB",0))<int(slots.get("DB",0)),
            }
            _bench_luxury=~x["position"].isin(["DL","DB"])
            # Exempt any currently unfilled required position.
            for _p,_open in _required_open.items():
                if _open:
                    _bench_luxury &= ~x["position"].eq(_p)
            x.loc[_bench_luxury,"evaluation_score"]-=1000.0
            x.loc[_bench_luxury,"elite_idp_quota_blocked"]=True

    # Fantasy Edge deep-bench competition.
    # Once RB5 or WR6 territory is reached, compare directly against the best remaining
    # eligible impact defender. Deep offense must clearly beat that defender on marginal value.
    # Deep-offense vs extra-IDP competition is owned by the single-authority
    # marginal-slot / strategic-value engine below. The obsolete hard block that
    # depended on marginal_roster_value has been removed so Live/Mock/Simulation
    # do not require a legacy column that is not part of the final authority.

    # Fantasy Edge extra-IDP quality guard.
    # After both required IDP starters are filled, a bench DL/DB must be an actual
    # impact option. Strongly negative roster opportunity cannot be overridden by name/rank.
    _idp_counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _required_idp_filled=(
        int(_idp_counts.get("DL",0))>=int(slots.get("DL",1)) and
        int(_idp_counts.get("DB",0))>=int(slots.get("DB",1))
    )
    if _required_idp_filled:
        _idp_mask_extra=x["position"].isin(["DL","DB"]) & x["idp_eligible"].fillna(False).astype(bool)
        _idp_ropp=_safe_num_series(x,"roster_opportunity_adj",0.0)
        _idp_tier=_safe_num_series(x,"idp_quality_tier",5.0)

        # Backup defender must be Tier 1-2 AND have acceptable roster opportunity.
        _elite_extra_ok=_idp_mask_extra & (_idp_tier<=2) & (_idp_ropp>=-18.0)
        _bad_extra=_idp_mask_extra & (~_elite_extra_ok)
        x.loc[_bad_extra,"evaluation_score"]-=5000.0
        x.loc[_bad_extra,"extra_idp_blocked"]=True

    # Fantasy Edge best-available IDP comparison.
    # Rank DL and DB *within the actually available pool* using the same inputs that drive
    # recommendations, so Brian Branch (or any other defender) must beat other available
    # same-position options rather than winning from a fixed name/rank prior.
    x["idp_available_rank"]=np.nan
    x["idp_available_score"]=np.nan
    x["idp_scarcity_cliff"]=0.0
    x["idp_scarcity_bonus"]=0.0

    for _p in ("DL","DB"):
        _pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if not _pm.any():
            continue

        _impact=pd.to_numeric(x.loc[_pm,"idp_impact_score"],errors="coerce").fillna(0.0)
        _talent=pd.to_numeric(x.loc[_pm,"idp_talent_score"],errors="coerce").fillna(0.0)
        _tier=pd.to_numeric(x.loc[_pm,"idp_quality_tier"],errors="coerce").fillna(5.0)
        _ext=pd.to_numeric(x.loc[_pm,"idp_external_rank"],errors="coerce")
        _proj=pd.to_numeric(x.loc[_pm,"projection"],errors="coerce").fillna(0.0)
        _vorp=pd.to_numeric(x.loc[_pm,"vorp"],errors="coerce").fillna(0.0)

        # Available-player composite:
        # fantasy impact and talent dominate; tier/external rank stabilize sparse rows;
        # projection/VORP provide direct scoring support where present.
        _ext_support=np.where(_ext.notna(),np.maximum(0.0,30.0-_ext)*0.22,0.0)
        _avail_score=(
            0.36*_impact +
            0.30*_talent +
            (6.0-_tier)*1.9 +
            _ext_support +
            0.18*_proj +
            0.45*np.maximum(_vorp,0.0)
        )

        x.loc[_pm,"idp_available_score"]=_avail_score
        x.loc[_pm,"idp_available_rank"]=pd.Series(
            _avail_score,index=x.index[_pm]
        ).rank(method="min",ascending=False)

        # Dynamic same-position scarcity: quantify the cliff from IDP1 to IDP2/3.
        _ranked_scores=pd.Series(_avail_score,index=x.index[_pm]).sort_values(ascending=False)
        if len(_ranked_scores)>=2:
            _cliff=float(_ranked_scores.iloc[0]-_ranked_scores.iloc[1])
        else:
            _cliff=6.0
        _best_idx=_ranked_scores.index[0]
        x.at[_best_idx,"idp_scarcity_cliff"]=_cliff
        if _cliff>=2.5:
            x.at[_best_idx,"evaluation_score"]+=min(8.0,2.0+_cliff*1.25)
            x.at[_best_idx,"idp_scarcity_bonus"]=min(8.0,2.0+_cliff*1.25)

        # Same-position authority: if an available defender trails the best option
        # by a meaningful amount, roster need cannot make him FINAL PICK instead.
        _best=float(np.nanmax(_avail_score))
        _gap=_best-_avail_score
        _clearly_worse=_gap>=4.0
        if np.any(_clearly_worse):
            _bad_idx=x.index[_pm][_clearly_worse]
            x.loc[_bad_idx,"evaluation_score"]-=18.0

        # Top-3 available defenders get a modest positive nudge, preserving timing logic.
        _ranks=pd.to_numeric(x.loc[_pm,"idp_available_rank"],errors="coerce")
        x.loc[_pm & x.index.isin(_ranks.index[_ranks<=3]),"evaluation_score"]+=4.0

    # Evidence authority after all roster construction: ineligible IDPs cannot be FINAL PICK.
    bad=x["position"].isin(["DL","DB"]) & (~x["idp_eligible"].fillna(False).astype(bool))
    x.loc[bad,"evaluation_score"]-=1000.0
    # v9.41 positional-quality dominance.
    # This fixes "last required DL/DB => any positive depth player becomes #1".
    for _p in ("DL","DB"):
        pm=x["position"].eq(_p) & x["idp_eligible"].fillna(False).astype(bool)
        if pm.any():
            best_tier=pd.to_numeric(x.loc[pm,"idp_quality_tier"],errors="coerce").min()
            if pd.notna(best_tier):
                worse=pm & (pd.to_numeric(x["idp_quality_tier"],errors="coerce") >= best_tier+2)
                x.loc[worse,"evaluation_score"]-=45.0

    _ropp_final=_safe_num_series(x,"roster_opportunity_adj",0.0)
    _good_fit=x[_ropp_final>=0]
    if len(_good_fit):
        _best_good=float(pd.to_numeric(_good_fit["evaluation_score"],errors="coerce").max())
        _badfit=(_ropp_final<=-5) & (pd.to_numeric(x["evaluation_score"],errors="coerce")<=_best_good+12.0)
        x.loc[_badfit,"evaluation_score"]-=1000.0

    cr=_safe_num_series(x,"market_pick",float(current_pick))
    local,ready,survive=execution_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),
        int(current_pick),next_pick,int(randomness)
    )
    x["survival_next"]=survive
    x["timing_ready"]=ready
    x["evaluation_rank"]=x.evaluation_score.rank(method="min",ascending=False)

    reach=np.maximum(cr-float(current_pick),0)  # player normally goes later = true reach
    fall=np.maximum(float(current_pick)-cr,0)   # player fell past market = value
    x["true_reach_picks"]=reach
    x["faller_value_picks"]=fall
    x["execution_score"]=x.evaluation_score.copy()

    # If a player is likely to survive, preserve the current pick for a scarcer option.
    x.loc[~x.timing_ready,"execution_score"]-=x.loc[~x.timing_ready,"survival_next"]*np.minimum(reach[~x.timing_ready],36)*.55

    # Hard reach protection: 24+ picks ahead of market needs a major evaluation edge.
    _best_eval=float(pd.to_numeric(x["evaluation_score"],errors="coerce").max()) if len(x) else -1e9
    _big_reach=(reach>=24)
    _insufficient_edge=pd.to_numeric(x["evaluation_score"],errors="coerce") < (_best_eval+4.0)
    x.loc[_big_reach & _insufficient_edge,"execution_score"]-=35.0

    # Falling past market is good, but only a modest timing bonus so late bench names
    # cannot overwhelm marginal roster value.
    x["execution_score"]+=.018*np.minimum(fall,48.0)
    # ------------------------------------------------------------------
    # Unified FINAL PICK layer shared by Live Draft and Interactive Mock.
    # Existing evaluation_score remains the mature player model. This final layer
    # adds transparent roster marginal value, snake-turn urgency and reach cost.
    # ------------------------------------------------------------------
    _uc=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _upos=x["position"].astype(str)

    def _uc_num(name,default=0.0):
        if name in x.columns:
            return pd.to_numeric(x[name],errors="coerce").fillna(float(default))
        return pd.Series(float(default),index=x.index,dtype=float)

    _proj=_uc_num("projection",0.0)
    _vorp=_uc_num("vorp",0.0)
    _eval=_uc_num("evaluation_score",-999.0)
    _market=_uc_num("market_pick",999.0)
    if "market_pick" not in x.columns and "consensus_rank" in x.columns:
        _market=_uc_num("consensus_rank",999.0)

    # Preserve the mature engine as the majority of player value while making
    # projection and VORP explicit enough to prevent unexplained same-position leaps.
    _player_value=0.74*_eval + 0.16*_vorp + 0.10*_proj

    _roster_value=np.zeros(len(x),dtype=float)
    for _p,_default_need in [("QB",1),("RB",2),("WR",2),("TE",1),("K",1),("DL",1),("DB",1)]:
        _have=int(_uc.get(_p,0))
        if _have < int(slots.get(_p,_default_need)):
            _roster_value += np.where(_upos.eq(_p),7.0,0.0)

    _rb=int(_uc.get("RB",0)); _wr=int(_uc.get("WR",0))
    if _rb>=4: _roster_value += np.where(_upos.eq("RB"),-4.0,0.0)
    if _rb>=5: _roster_value += np.where(_upos.eq("RB"),-8.0,0.0)
    if _wr>=5: _roster_value += np.where(_upos.eq("WR"),-6.0,0.0)

    # Snake-turn urgency: candidates unlikely to survive to the user's next turn
    # receive a bounded bonus. This is never a legality override.
    _next_gap=max(int(next_pick)-int(current_pick),1)
    _survival_margin=_market-float(current_pick)
    _next_turn_risk=np.clip((_next_gap-_survival_margin)/max(_next_gap,1),0,1)*6.0

    # Continuous reach cost.
    _reach=np.maximum(_market-float(current_pick),0.0)
    _reach_cost=np.minimum(_reach,48.0)*0.14

    # Controlled IDP portfolio: 1 DL + 1 DB required; third IDP is purely merit-based.
    _idp=_upos.isin(["DL","DB"])
    _idp_total=int(_uc.get("DL",0))+int(_uc.get("DB",0))
    _tier=_uc_num("idp_quality_tier",5.0)
    _impact=_uc_num("idp_impact_score",0.0)
    _eligible=x["idp_eligible"].fillna(False).astype(bool) if "idp_eligible" in x.columns else pd.Series(False,index=x.index)
    _impact_idp=_idp & _eligible & (_tier<=2)
    _idp_marginal=np.zeros(len(x),dtype=float)

    if _idp_total<2:
        _idp_marginal += np.where(_impact_idp,3.5+np.minimum(_impact,15.0)*0.10,0.0)
    elif _idp_total==2 and int(round_no)>=11:
        # Third IDP receives no structural bonus. Quality, scarcity, opportunity cost
        # and rollout value must make it win naturally.
        _idp_marginal += 0.0
    elif _idp_total>=3:
        # Fourth IDP is effectively prohibited for this 17-player roster.
        _idp_marginal += np.where(_idp,-80.0,0.0)

    x["player_value_component"]=_player_value
    x["roster_value_component"]=_roster_value
    x["next_turn_risk_component"]=_next_turn_risk
    x["reach_cost_component"]=_reach_cost
    x["idp_marginal_component"]=_idp_marginal
    x["unified_pick_score"]=_player_value+_roster_value+_next_turn_risk+_idp_marginal-_reach_cost

    # Same-position projection/VORP sanity guard.
    x["same_position_value_guard"]=False
    for _p in x["position"].dropna().astype(str).unique():
        _m=_upos.eq(_p)
        if int(_m.sum())<2:
            continue
        _best_proj=float(_proj[_m].max())
        _best_vorp=float(_vorp[_m].max())
        _dominated=_m & (_proj < _best_proj-1.5) & (_vorp < _best_vorp-1.0)
        if _dominated.any() and (_m & ~_dominated).any():
            _best_good=float(x.loc[_m & ~_dominated,"unified_pick_score"].max())
            _weak=_dominated & (x["unified_pick_score"] < _best_good+4.0)
            x.loc[_weak,"unified_pick_score"]-=8.0
            x.loc[_weak,"same_position_value_guard"]=True

    # Absolute post-pick roster feasibility gate.
    _counts_now=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    _remaining_after=max(int(exact_roster_rounds(slots))-int(round_no),0)

    def _min_required_after(_after):
        fixed={p:max(int(slots.get(p,0))-int(_after.get(p,0)),0) for p in ["QB","RB","WR","TE","K","DL","DB"]}
        skill_need=int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+int(slots.get("FLEX",0))
        skill_have=int(_after.get("RB",0))+int(_after.get("WR",0))+int(_after.get("TE",0))
        flex_extra=max(skill_need-skill_have-(fixed["RB"]+fixed["WR"]+fixed["TE"]),0)
        return int(sum(fixed.values())+flex_extra)

    x["post_pick_feasible"]=True
    for _p in ["QB","RB","WR","TE","K","DL","DB"]:
        _pm=x["position"].astype(str).eq(_p)
        if _pm.any():
            _after=dict(_counts_now); _after[_p]=int(_after.get(_p,0))+1
            if _min_required_after(_after)>_remaining_after:
                x.loc[_pm,"post_pick_feasible"]=False

    if int(_counts_now.get("DL",0))+int(_counts_now.get("DB",0))>=3:
        x.loc[x["position"].isin(["DL","DB"]),"post_pick_feasible"]=False

    # Single authoritative Live/Mock decision engine.
    x=_single_authority_final(
        x,roster,slots,int(round_no),int(current_pick),int(next_pick),
        compute_stability=not _reuse_sim_idp,
        rollout_branches=3 if _reuse_sim_idp else 10
    )

    # FINAL PICK has one authority plus non-negotiable quality/legality gates.
    x["execution_score"]=x["final_pick_value"]
    _hard_block=~x["post_pick_feasible"]
    for _flag in ["roster_completion_blocked","same_pos_dominated","idp_quality_blocked","extra_idp_blocked","deep_skill_hard_cap"]:
        if _flag in x.columns:
            _hard_block |= x[_flag].fillna(False).astype(bool)
    _idp_now=int(_counts_now.get("DL",0))+int(_counts_now.get("DB",0))
    if _idp_now>=3:
        _hard_block |= x["position"].isin(["DL","DB"])
    _mrv=_safe_num_series(x,"marginal_roster_value",0.0)
    _vorp=_safe_num_series(x,"vorp",0.0)
    _proj=_safe_num_series(x,"projection",0.0)
    _ropp=_safe_num_series(x,"roster_opportunity_adj",0.0)

    for _p in ["RB","WR"]:
        _have=int(_counts_now.get(_p,0))
        if _have>=5:
            _pm=x["position"].astype(str).eq(_p) & (~_hard_block)
            _alt=(~x["position"].astype(str).eq(_p)) & (~_hard_block)
            if _pm.any() and _alt.any():
                _best_alt_mrv=float(_mrv[_alt].max())
                _best_alt_vorp=float(_vorp[_alt].max())
                _best_alt_proj=float(_proj[_alt].max())
                _premium=(
                    (_mrv >= _best_alt_mrv+1.25) &
                    ((_vorp >= _best_alt_vorp+0.60) | (_proj >= _best_alt_proj+1.0)) &
                    (_ropp >= -1.5)
                )
                _hard_block |= _pm & (~_premium)

    _minimum_now,_,_=_minimum_required_picks_remaining(_counts_now,slots)
    x["cross_position_dominated"]=False
    if _minimum_now==0:
        _candidate_mask=~_hard_block
        _indices=list(x.index[_candidate_mask])
        for _idx in _indices:
            _others=_candidate_mask.copy()
            _others.loc[_idx]=False
            if not _others.any():
                continue
            _dom=(
                (_mrv[_others] >= float(_mrv.loc[_idx])+1.0) &
                (_vorp[_others] >= float(_vorp.loc[_idx])+0.40) &
                (_proj[_others] >= float(_proj.loc[_idx])+0.50) &
                (_ropp[_others] >= float(_ropp.loc[_idx]))
            )
            if bool(_dom.any()):
                x.at[_idx,"cross_position_dominated"]=True
        _hard_block |= x["cross_position_dominated"].fillna(False).astype(bool)

    if int(round_no)>=11:
        _nonnegative=(~_hard_block) & (_ropp>=0.0)
        if _nonnegative.any():
            _hard_block |= (~_hard_block) & (_ropp<-5.0)

        # V6.14 late optional quality floor: once a position's required starter
        # count is satisfied, do not spend a bench spot on negative VORP when a
        # legal nonnegative-VORP alternative exists. Required completion is exempt.
        _counts_late=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
        _required_pos=pd.Series(False,index=x.index,dtype=bool)
        for _p in ["QB","RB","WR","TE","K","DL","DB"]:
            if int(_counts_late.get(_p,0)) < int(slots.get(_p,0)):
                _required_pos |= x["position"].astype(str).eq(_p)
        _optional=(~_hard_block) & (~_required_pos)
        _good_optional=_optional & (_vorp>=0.0) & (_ropp>=-2.0)
        if _good_optional.any():
            _hard_block |= _optional & (_vorp<0.0)

    # Market-efficient reach guard. Avoid paying 18+ picks ahead of market when
    # another legal candidate has comparable VORP/marginal value and is priced
    # near the current pick. This directly attacks avoidable Draft Value loss.
    _market_final=_safe_num_series(x,"market_pick",float(current_pick)+20.0)
    _reach_gap=_market_final-float(current_pick)
    x["raw_reach_gap"]=_reach_gap
    x["avoidable_reach"]=False
    _legal_now=~_hard_block
    _near_market=_legal_now & (_reach_gap<=12.0)
    if _near_market.any():
        for _idx in list(x.index[_legal_now & (_reach_gap>=13.0)]):
            _similar=(
                _near_market &
                (_vorp >= float(_vorp.loc[_idx])-0.90) &
                (_mrv >= float(_mrv.loc[_idx])-1.75) &
                (_ropp >= float(_ropp.loc[_idx])-1.00)
            )
            if bool(_similar.any()):
                x.at[_idx,"avoidable_reach"]=True
                _hard_block.loc[_idx]=True

    # V6.18 draft-day status guard: DND/IR/NFI-level statuses must be true
    # hard exclusions, not merely a clipped score penalty.
    _injury_exec=_safe_num_series(x,"injury_penalty",0.0)
    _status_hard=_injury_exec>=900.0
    x["status_hard_blocked"]=_status_hard
    _hard_block |= _status_hard

    x["final_quality_blocked"]=_hard_block
    x.loc[_hard_block,"execution_score"]=-1e12

    # Final challenger test: a candidate cannot win on timing/rollout alone when
    # another legal player offers a clearly superior value package.
    _legal_value=~x["final_quality_blocked"]
    _mrv_final=_safe_num_series(x,"marginal_roster_value",0.0)
    _vorp_final=_safe_num_series(x,"vorp",0.0)
    _proj_final=_safe_num_series(x,"projection",0.0)
    _market_final2=_safe_num_series(x,"market_pick",float(current_pick)+20.0)
    _ropp_cmp=_safe_num_series(x,"roster_opportunity_adj",0.0)
    x["value_challenger_blocked"]=False

    _legal_indices=list(x.index[_legal_value])
    for _idx in _legal_indices:
        _others=_legal_value.copy()
        _others.loc[_idx]=False
        if not _others.any():
            continue
        _challenger=(
            _others &
            (_mrv_final >= float(_mrv_final.loc[_idx])+1.5) &
            (_vorp_final >= float(_vorp_final.loc[_idx])+0.5) &
            (_ropp_cmp >= float(_ropp_cmp.loc[_idx])-0.5) &
            (_market_final2 <= float(_market_final2.loc[_idx])+10.0)
        )
        if bool(_challenger.any()):
            x.at[_idx,"value_challenger_blocked"]=True
            x.at[_idx,"execution_score"]-=750.0

    _ropp_final=_safe_num_series(x,"roster_opportunity_adj",0.0)
    _feasible_now=~x["final_quality_blocked"]
    if (_feasible_now & (_ropp_final>=0)).any():
        _luxury_cut=-3.0 if int(round_no)>=11 else -6.0
        _bad_luxury=_feasible_now & (_ropp_final<_luxury_cut)
        x.loc[_bad_luxury,"execution_score"]-=325.0

    x=_v944_add_idp_display_metrics(x)

    return x.sort_values("execution_score",ascending=False), local




def _v633_active_roster_directory(players):
    """Build a clean active NFL roster directory from the Sleeper NFL player feed.
    This is an identity/status source only; it never manufactures fantasy value.
    """
    cols=["player_id","player","position","raw_position","team","active","injury_status","years_exp"]
    if not isinstance(players, dict) or not players:
        return pd.DataFrame(columns=cols)
    rows=[]
    allowed={"QB","RB","WR","TE","K","DL","DB"}
    for pid,pl in players.items():
        if not isinstance(pl,dict) or pl.get("active") is False:
            continue
        raw=str(pl.get("position") or "").upper().strip()
        pos=canonical_position(raw)
        team=str(pl.get("team") or "").upper().strip()
        # Active roster export = currently attached to an NFL team.
        if pos not in allowed or not team or team in {"FA","NONE","N/A"}:
            continue
        name=pl.get("full_name") or " ".join([pl.get("first_name") or "",pl.get("last_name") or ""]).strip()
        if not name:
            continue
        rows.append({
            "player_id":str(pid),"player":str(name),"position":pos,"raw_position":raw,
            "team":team,"active":True,"injury_status":pl.get("injury_status") or "",
            "years_exp":pl.get("years_exp")
        })
    if not rows:
        return pd.DataFrame(columns=cols)
    out=pd.DataFrame(rows)
    out["key"]=out["player"].map(norm)
    return out.sort_values(["position","team","player"]).drop_duplicates("key",keep="first").reset_index(drop=True)

@st.cache_data(ttl=21600, show_spinner=False)
def _v637_consensus_directory_ranks():
    """Fetch current 2026 FantasyPros PPR consensus ranks for display enrichment.
    This never changes the certified recommendation engine; it only gives roster
    directory players a real external rank when the player is actually ranked.
    """
    try:
        url="https://www.fantasypros.com/nfl/fantasy-football-rankings/ppr-overall.php"
        tables=pd.read_html(url)
        frames=[]
        for t in tables:
            cols=[str(c).strip().lower() for c in t.columns]
            if any(c in cols for c in ["rk","rank"]) and any("player" in c for c in cols):
                tt=t.copy(); tt.columns=cols; frames.append(tt)
        if not frames:
            return pd.DataFrame(columns=["key","external_ecr_rank"])
        raw=max(frames,key=len)
        rank_col="rk" if "rk" in raw.columns else "rank"
        player_col=next(c for c in raw.columns if "player" in c)
        out=pd.DataFrame({
            "player_raw":raw[player_col].astype(str),
            "external_ecr_rank":pd.to_numeric(raw[rank_col],errors="coerce")
        }).dropna(subset=["external_ecr_rank"])
        # FantasyPros table cells can include team/position text after the name.
        # Prefer matching by the clean name prefix generated from known roster names
        # later; retain normalized full cell as a secondary key.
        out["key_full"]=out.player_raw.map(norm)
        return out.drop_duplicates("external_ecr_rank").reset_index(drop=True)
    except Exception as e:
        pass  # V7.04: cached loaders must not mutate st.session_state
        return pd.DataFrame(columns=["player_raw","external_ecr_rank","key_full"])

def _v637_attach_directory_ranks(roster_dir):
    if roster_dir is None or roster_dir.empty:
        return roster_dir
    x=roster_dir.copy()
    x["external_ecr_rank"]=np.nan
    ranks=_v637_consensus_directory_ranks()
    if ranks is None or ranks.empty:
        return x
    # Match each active roster name against the beginning of the FantasyPros cell.
    cells=[(str(r.player_raw),float(r.external_ecr_rank)) for _,r in ranks.iterrows()]
    def lookup(name):
        nk=norm(name)
        hits=[]
        for cell,rk in cells:
            ck=norm(cell)
            if ck.startswith(nk): hits.append(rk)
        return min(hits) if hits else np.nan
    x["external_ecr_rank"]=x.player.astype(str).map(lookup)
    return x


def _v642_enrich_ranked_roster_players(board, roster_dir, max_ecr=260):
    """Add fantasy-relevant active roster players missing from the certified board.

    Only players with a real current external consensus rank are eligible.  Their
    projection / VORP / draft score are interpolated from Fantasy Edge's existing
    same-position ranked curve, so we never fall back to the old 999/-4 placeholder
    values.  These rows are explicitly tagged ECR_ENRICHED and use lower confidence.
    """
    if board is None or len(board)==0 or roster_dir is None or len(roster_dir)==0:
        return board
    x=board.copy()
    if "key" not in x.columns:
        x["key"]=x["player"].astype(str).map(norm)
    existing=set(x["key"].astype(str))
    rd=roster_dir.copy()
    rd["external_ecr_rank"]=pd.to_numeric(rd.get("external_ecr_rank"),errors="coerce")
    rd=rd[rd["external_ecr_rank"].notna() & (rd["external_ecr_rank"]<=float(max_ecr))].copy()
    rd=rd[~rd["key"].astype(str).isin(existing)]
    if rd.empty:
        return x

    repl={"QB":16.0,"RB":8.2,"WR":7.6,"TE":5.6,"DL":6.2,"DB":5.9,"K":8.1}
    rows=[]
    for _,r in rd.iterrows():
        pos=str(r.get("position") or "")
        ecr=float(r["external_ecr_rank"])
        peers=x[x["position"].astype(str).eq(pos)].copy()
        peers["market_pick"]=pd.to_numeric(peers.get("market_pick"),errors="coerce")
        peers["projection"]=pd.to_numeric(peers.get("projection"),errors="coerce")
        peers["draft_score"]=pd.to_numeric(peers.get("draft_score"),errors="coerce")
        peers=peers.dropna(subset=["market_pick","projection"]).sort_values("market_pick")
        if len(peers)<2:
            continue
        xp=peers["market_pick"].to_numpy(dtype=float)
        proj=float(np.interp(ecr,xp,peers["projection"].to_numpy(dtype=float),left=peers["projection"].iloc[0],right=peers["projection"].iloc[-1]))
        ds_peers=peers.dropna(subset=["draft_score"])
        if len(ds_peers)>=2:
            ds=float(np.interp(ecr,ds_peers["market_pick"].to_numpy(dtype=float),ds_peers["draft_score"].to_numpy(dtype=float),left=ds_peers["draft_score"].iloc[0],right=ds_peers["draft_score"].iloc[-1]))
        else:
            ds=float(100.0-ecr*0.45)
        replacement=float(repl.get(pos,0.0))
        vorp=float(proj-replacement)
        d={c:np.nan for c in x.columns}
        d.update({
            "player":str(r.get("player")),"position":pos,"raw_position":str(r.get("raw_position") or pos),
            "team":str(r.get("team") or "NFL"),"key":str(r.get("key")),
            "market_pick":ecr,"consensus_rank":ecr,"projection":proj,"replacement_ppg":replacement,
            "vorp":vorp,"draft_score":ds,"pure_model_score":ds,"last_ppg":proj,"prior_ppg":proj,
            "opp_pg":proj,"progression":0.0,"regression":0.0,"scarcity":0.0,
            "consensus_strength":max(0.0,100.0*(1.0-np.log(max(ecr,1.0))/np.log(300.0))),
            "confidence":0.60,"injury":str(r.get("injury_status") or ""),"injury_severity":0,
            "injury_penalty":0.0,"role_score":0.0,"profile":"Consensus-enriched active roster",
            "age":np.nan,"exp":pd.to_numeric(pd.Series([r.get("years_exp")]),errors="coerce").iloc[0],
            "breakout":0.0,"decline":0.0,"waiver_score":proj*4.0,
            "display_projection":proj,"display_vorp":vorp,"display_model_rank":np.nan,
            "model_rank":np.nan,"id":"roster-ecr:"+str(r.get("key")),
            "identity_key":"roster-ecr:"+str(r.get("key"))+"|"+pos,
            "pool_status":"ECR_ENRICHED","roster_sync_source":"Active roster + current ECR",
            "external_ecr_rank":ecr,
        })
        rows.append(d)
    if not rows:
        return x
    add=pd.DataFrame(rows)
    for c in x.columns:
        if c not in add.columns: add[c]=np.nan
    for c in add.columns:
        if c not in x.columns: x[c]=np.nan
    out=pd.concat([x,add[x.columns]],ignore_index=True)
    return out.drop_duplicates("key",keep="first").reset_index(drop=True)

def _v633_merge_active_roster_directory(board, roster_dir):
    """Guarantee every active NFL roster player is selectable in Draft/Mock.
    Missing directory players enter as DEPTH_ONLY with conservative placeholder
    values so identity completeness cannot create fake DRAFT NOW recommendations.
    Ranked players keep all certified Fantasy Edge values.
    """
    if board is None or len(board)==0 or roster_dir is None or len(roster_dir)==0:
        return board
    x=board.copy()
    if "key" not in x.columns:
        x["key"]=x["player"].astype(str).map(norm)
    if "pool_status" not in x.columns:
        x["pool_status"]="RANKED"
    if "roster_sync_source" not in x.columns:
        x["roster_sync_source"]="Fantasy Edge"
    existing=set(x["key"].astype(str))
    repl={"QB":16.0,"RB":8.2,"WR":7.6,"TE":7.8,"K":7.0,"DL":6.2,"DB":5.9}
    rows=[]
    for _,r in roster_dir.iterrows():
        key=str(r["key"]); pos=str(r["position"]); name=str(r["player"]); team=str(r["team"])
        if key in existing:
            m=x["key"].astype(str).eq(key)
            x.loc[m,"team"]=team
            x.loc[m,"roster_sync_source"]="Active NFL roster"
            continue
        base=float(repl.get(pos,7.0))
        d={c:np.nan for c in x.columns}
        d.update({
            "id":"roster:"+str(r["player_id"]),"player":name,"key":key,
            "position":pos,"raw_position":str(r.get("raw_position",pos)),"team":team,
            "projection":max(0.0,base-4.0),"vorp":-4.0,"replacement_ppg":base,
            "draft_score":-999.0,"model_rank":999.0,"consensus_rank":999.0,"market_pick":999.0,
            "confidence":0.10,"injury":str(r.get("injury_status","") or ""),"injury_penalty":0.0,
            "v9_market_pick":999.0,"v9_vorp":-4.0,"v9_draft_score":-999.0,
            "v9_model_rank":999.0,"v9_base_live_score":-999.0,
            "pool_status":"DEPTH_ONLY","roster_sync_source":"Active NFL roster"
        })
        rows.append(d)
        existing.add(key)
    if rows:
        x=pd.concat([x,pd.DataFrame(rows)],ignore_index=True,sort=False)
    return x.drop_duplicates("key",keep="first").reset_index(drop=True)

def make_board(players, hist, market, ppr, pass_td, idp, teams, slots):
    rows=[]
    for pid,p in players.items():
        rawpos=p.get("position")
        grp=canonical_position(rawpos)
        if grp not in ["QB","RB","WR","TE","K","DL","DB"] or p.get("active") is False: continue
        name=p.get("full_name") or " ".join([p.get("first_name") or "",p.get("last_name") or ""]).strip()
        if not name: continue
        rows.append({"id":str(pid),"player":name,"key":norm(name),"position":grp,"raw_position":rawpos,
                     "team":p.get("team") or "FA","age":p.get("age"),"exp":p.get("years_exp"),
                     "injury":p.get("injury_status")})
    b=pd.DataFrame(rows)
    if b.empty: return b

    if hist.empty:
        b["last_ppg"]=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"K":8.5,"DL":6,"DB":5.5})
        b["prior_ppg"]=b.last_ppg*.9
        for c in ["opp_pg","td_rate_z","eff_z","growth_z","opp_z","idp_vol_z","bigplay_z"]:
            b[c]=0.
    else:
        h=hist.copy()
        if "position_group" not in h.columns:
            h["position_group"]=h["position"].map(position_group)
        yr=int(h.season.max())
        cur=h[h.season.eq(yr)].copy()
        prev=h[h.season.eq(yr-1)][["key","position_group","ppr_ppg"]].rename(columns={"ppr_ppg":"prior_off_ppg"})
        cur=cur.merge(prev,on=["key","position_group"],how="left")

        # Offensive features.
        cur["opp_pg"]=(cur.targets.fillna(0)+cur.carries.fillna(0))/cur.games
        touches=(cur.receptions.fillna(0)+cur.carries.fillna(0)).clip(lower=1)
        cur["td_rate"]=(cur.receiving_tds.fillna(0)+cur.rushing_tds.fillna(0))/touches
        cur["eff"]=(cur.receiving_yards.fillna(0)+cur.rushing_yards.fillna(0))/touches

        # IDP fantasy points using user scoring.
        cur["idp_points"]=(
            cur.def_tackles_solo.fillna(0)*idp["solo"]
            + cur.def_tackles_with_assist.fillna(0)*idp["assist"]
            + cur.def_sacks.fillna(0)*idp["sack"]
            + cur.def_tackles_for_loss.fillna(0)*idp["tfl"]
            + cur.def_qb_hits.fillna(0)*idp["qb_hit"]
            + cur.def_interceptions.fillna(0)*idp["int"]
            + cur.def_pass_defended.fillna(0)*idp["pd"]
            + cur.def_fumbles_forced.fillna(0)*idp["ff"]
            + cur.def_fumble_recovery_opp.fillna(0)*idp["fr"]
            + cur.def_tds.fillna(0)*idp["def_td"]
            + cur.def_safety.fillna(0)*idp["safety"]
        )
        cur["idp_ppg"]=cur.idp_points/cur.games
        cur["idp_volume"]=(cur.def_tackles_solo.fillna(0)+cur.def_tackles_with_assist.fillna(0)+
                           cur.def_sacks.fillna(0)*2+cur.def_pass_defended.fillna(0))/cur.games
        cur["bigplay_rate"]=(cur.def_sacks.fillna(0)+cur.def_interceptions.fillna(0)+
                             cur.def_fumbles_forced.fillna(0)+cur.def_tds.fillna(0))/cur.games

        # Prior IDP season from raw h.
        prv=h[h.season.eq(yr-1)].copy()
        prv["prior_idp_points"]=(
            prv.def_tackles_solo.fillna(0)*idp["solo"] + prv.def_tackles_with_assist.fillna(0)*idp["assist"]
            + prv.def_sacks.fillna(0)*idp["sack"] + prv.def_tackles_for_loss.fillna(0)*idp["tfl"]
            + prv.def_qb_hits.fillna(0)*idp["qb_hit"] + prv.def_interceptions.fillna(0)*idp["int"]
            + prv.def_pass_defended.fillna(0)*idp["pd"] + prv.def_fumbles_forced.fillna(0)*idp["ff"]
            + prv.def_fumble_recovery_opp.fillna(0)*idp["fr"] + prv.def_tds.fillna(0)*idp["def_td"]
            + prv.def_safety.fillna(0)*idp["safety"]
        )
        prv["prior_idp_ppg"]=prv.prior_idp_points/prv.games
        if "position_group" not in prv.columns:
            prv["position_group"]=prv["position"].map(position_group)
        cur=cur.merge(prv[["key","position_group","prior_idp_ppg"]],on=["key","position_group"],how="left")

        cur["last_ppg"]=np.where(cur.position.isin(["DL","DB"]),cur.idp_ppg,cur.ppr_ppg)
        cur["prior_ppg"]=np.where(cur.position.isin(["DL","DB"]),cur.prior_idp_ppg,cur.prior_off_ppg)
        cur["prior_ppg"]=pd.to_numeric(cur["prior_ppg"],errors="coerce")
        cur["prior_ppg"]=cur.prior_ppg.fillna(cur.last_ppg*.88)
        cur["growth"]=cur.last_ppg-cur.prior_ppg

        for c in ["td_rate","eff","growth","opp_pg","idp_volume","bigplay_rate"]:
            sd=cur[c].std()
            cur[c+"_z"]=(cur[c]-cur[c].median())/(sd if pd.notna(sd) and sd else 1)

        keep=["key","position_group","last_ppg","prior_ppg","opp_pg","td_rate_z","eff_z","growth_z","opp_pg_z",
              "idp_volume_z","bigplay_rate_z"]
        cur=cur[keep].rename(columns={"opp_pg_z":"opp_z","idp_volume_z":"idp_vol_z","bigplay_rate_z":"bigplay_z"})
        b=b.merge(cur,left_on=["key","position"],right_on=["key","position_group"],how="left")
        b.drop(columns=["position_group"],inplace=True,errors="ignore")

        base=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"K":8.5,"DL":6,"DB":5.5})
        b["last_ppg"]=b.last_ppg.fillna(base)
        b["prior_ppg"]=b.prior_ppg.fillna(b.last_ppg*.9)
        for c in ["opp_pg","td_rate_z","eff_z","growth_z","opp_z","idp_vol_z","bigplay_z"]:
            b[c]=b[c].fillna(0)

    if market is not None and not market.empty:
        b=b.merge(market[["key","consensus_pos","consensus_rank","consensus_page"]],
                  left_on=["key","position"],right_on=["key","consensus_pos"],how="left")
        b.drop(columns=["consensus_pos"],inplace=True,errors="ignore")
    else:
        b["consensus_rank"]=np.nan
        b["consensus_page"]=""

    b["age"]=pd.to_numeric(b.age,errors="coerce")
    b["exp"]=pd.to_numeric(b.exp,errors="coerce").fillna(0)
    young=np.select([b.age<=22,b.age<=24,b.age<=26,b.age<=29],[16,12,7,2],default=-5)
    early=np.select([b.exp<=1,b.exp<=2,b.exp<=4],[10,7,3],default=0)

    is_idp=b.position.isin(["DL","DB"])
    # Offensive progression/regression.
    b["progression"]=50+b.growth_z*14+b.opp_z*11+young+early
    b["regression"]=50+b.td_rate_z*18+b.eff_z*10-b.opp_z*12
    # IDP: tackle/pressure volume is more repeatable; big-play spikes are more regression-prone.
    b.loc[is_idp,"progression"]=50+b.loc[is_idp,"growth_z"]*12+b.loc[is_idp,"idp_vol_z"]*15+young[is_idp]+early[is_idp]
    b.loc[is_idp,"regression"]=50+b.loc[is_idp,"bigplay_z"]*20-b.loc[is_idp,"idp_vol_z"]*12

    b["breakout"]=1/(1+np.exp(-(b.progression-55)/13))
    b["decline"]=1/(1+np.exp(-(b.regression-60)/12))

    # "Breakout" is reserved for genuinely ascending/early-career players.
    young_breakout=(b.age.fillna(99)<=26) & (b.exp<=4)
    b["profile"]="Stable / neutral"
    b.loc[b.decline>=.68,"profile"]="Decline risk"
    b.loc[(b.decline>=.50)&(b.decline<.68),"profile"]="High variance"
    b.loc[young_breakout & (b.breakout>=.67),"profile"]="Breakout target"
    b.loc[young_breakout & (b.breakout.between(.55,.67, inclusive="left")),"profile"]="Ascending"
    b.loc[(~young_breakout) & (b.breakout>=.65) & (b.decline<.50),"profile"]="Veteran upside"

    base=b.position.map({"QB":16,"RB":8.5,"WR":8,"TE":6,"K":8.5,"DL":6,"DB":5.5})
    b["projection"]=(b.last_ppg*.70+b.prior_ppg*.20+base*.10+b.growth_z*.50).clip(lower=1)

    # v9.50 kicker valuation: K has no nflverse fantasy-history feed in this build,
    # so do NOT leave every kicker at the same 8.5 projection.
    # Use the live market ordering already attached to the board as a conservative
    # relative projection proxy. This creates real separation without inventing a
    # player-name whitelist.
    _km=b.position.eq("K")
    if _km.any():
        # make_board has consensus_rank at this stage; market_pick is attached later.
        # Use consensus rank when available and fall back to deterministic row order.
        if "consensus_rank" in b.columns:
            _kmarket=pd.to_numeric(b.loc[_km,"consensus_rank"],errors="coerce")
        else:
            _kmarket=pd.Series(np.nan,index=b.index[_km],dtype=float)

        _fallback=pd.Series(
            np.arange(1,int(_km.sum())+1,dtype=float),
            index=b.index[_km]
        )
        # Missing K consensus values sort behind known market-ranked kickers.
        if _kmarket.notna().any():
            _max_known=float(_kmarket.max())
            _kmarket=_kmarket.fillna(_max_known + _fallback)
        else:
            _kmarket=_fallback

        _krank=_kmarket.rank(method="min",ascending=True,na_option="bottom")
        _kn=max(int(_km.sum()),1)
        _kpct=1.0-((_krank-1.0)/max(_kn-1,1))
        b.loc[_km,"projection"]=7.35 + 2.15*_kpct

    skill=b.position.isin(["RB","WR","TE"])
    b.loc[skill,"projection"] += (ppr-1.0)*np.clip(b.loc[skill,"opp_pg"]*.55,1,8)
    if pass_td!=4:
        qb=b.position.eq("QB"); b.loc[qb,"projection"] += (pass_td-4)*1.5

    b["draft_score"]=b.projection*5+b.progression*.18-b.regression*.12
    b["waiver_score"]=b.projection*4+b.progression*.23-b.regression*.10

    # Value Over Replacement Player (VORP): raw points above a realistic replacement starter.
    flex=float(slots.get("FLEX",0))
    # FLEX demand is distributed mostly to WR/RB in PPR, with a small TE share.
    replacement_slots={
        "QB":max(teams*int(slots.get("QB",1)),teams),
        "RB":max(int(round(teams*(float(slots.get("RB",2))+flex*.38))),teams),
        "WR":max(int(round(teams*(float(slots.get("WR",2))+flex*.55))),teams),
        "TE":max(int(round(teams*(float(slots.get("TE",1))+flex*.07))),teams),
        "K":max(teams*int(slots.get("K",1)),teams),
        "DL":max(teams*int(slots.get("DL",1)),teams),
        "DB":max(teams*int(slots.get("DB",1)),teams)
    }
    repl={}
    for pos,n in replacement_slots.items():
        vals=b.loc[b.position.eq(pos),"projection"].sort_values(ascending=False).reset_index(drop=True)
        idx=min(max(int(n)-1,0),len(vals)-1) if len(vals) else 0
        repl[pos]=float(vals.iloc[idx]) if len(vals) else 0.0
    b["replacement_ppg"]=b.position.map(repl).fillna(0)
    b["vorp"]=b.projection-b.replacement_ppg

    # v9.50: kicker VORP is position-relative, using the 12-team replacement line.
    # This prevents every K from displaying 0.0 VORP.
    _km=b.position.eq("K")
    if _km.any():
        _kvals=pd.to_numeric(b.loc[_km,"projection"],errors="coerce").sort_values(ascending=False)
        _krep_idx=min(max(int(teams)-1,0),len(_kvals)-1)
        _krep=float(_kvals.iloc[_krep_idx]) if len(_kvals) else 7.35
        b.loc[_km,"replacement_ppg"]=_krep
        b.loc[_km,"vorp"]=pd.to_numeric(b.loc[_km,"projection"],errors="coerce")-_krep

    # Pure model score before market consensus: this is where we intentionally disagree with consensus.
    scarcity=b.position.map({"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"K":-1.25,"DL":-0.35,"DB":-0.45}).fillna(0)
    b["pure_model_score"]=b.vorp*9+b.projection*1.6+b.progression*.12-b.regression*.10+scarcity
    b["model_rank"]=b.pure_model_score.rank(method="min",ascending=False)

    # Weekly-updated expert consensus acts as a reality check, not the engine.
    if b.consensus_rank.notna().any():
        maxrank=max(float(b.consensus_rank.max()),250.0)
        b["consensus_strength"]=(100*(1-np.log(b.consensus_rank.clip(lower=1))/np.log(maxrank))).clip(0,100)
    else:
        b["consensus_strength"]=50.0
    b["consensus_strength"]=b.consensus_strength.fillna(45.0)
    b["draft_score"]=b.pure_model_score+b.consensus_strength*.10
    b["consensus_edge"]=b.consensus_rank-b.model_rank

    # Confidence rises when we have history + consensus and falls with current injury flags.
    hist_conf=np.where(b.last_ppg.notna(),.20,0)
    market_conf=np.where(b.consensus_rank.notna(),.20,0)
    injury_pen=np.where(b.injury.fillna("").isin(["Out","IR","PUP"]),.25,0)
    agreement=np.where(b.consensus_rank.notna(), np.clip(1-np.abs(b.consensus_edge)/60,0,1)*.15, .05)
    b["confidence"]=(.40+hist_conf+market_conf+agreement-injury_pen).clip(.30,.95)
    # Stable identity guardrail: keep the canonical Sleeper position attached to each player ID.
    b["position"]=[validate_position(pl,pos) for pl,pos in zip(b.player,b.position)]
    b["identity_key"]=b["id"].astype(str)+"|"+b["position"].astype(str)
    return b.sort_values("draft_score",ascending=False).reset_index(drop=True)


def snake_pick(round_no, slot, teams):
    return (round_no-1)*teams + (slot if round_no % 2 else teams-slot+1)

def next_user_pick(current_overall, slot, teams, rounds):
    picks=[snake_pick(r,slot,teams) for r in range(1,rounds+1)]
    return next((p for p in picks if p>current_overall), None)

def survival_probability(consensus_rank, next_pick, randomness=12):
    if pd.isna(consensus_rank) or next_pick is None:
        return np.nan
    # Smooth probability that a player with consensus rank survives to a future pick.
    scale=max(float(randomness),4.0)
    z=(float(consensus_rank)-float(next_pick))/scale
    return float(1/(1+np.exp(-z)))


def survival_probability_array(market_pick, next_pick, randomness=12):
    """Probability a player remains available until our next snake-draft pick."""
    x=np.asarray(market_pick,dtype=float)
    if next_pick is None:
        return np.zeros_like(x,dtype=float)
    scale=max(float(randomness)*1.15,5.0)
    z=(x-float(next_pick))/scale
    return 1/(1+np.exp(-z))


def late_survival_probability_array_empirical(market_pick, next_pick, slot, round_no):
    """V7.54 challenger-only empirical R11+ survival lookup.

    Frozen from V7.53 calibration. Uses slot + round + market-minus-next-pick band,
    with clipping and simple backoff. This does NOT change the live V7.50 champion.
    """
    x=np.asarray(market_pick,dtype=float)
    if next_pick is None:
        return np.zeros_like(x,dtype=float)

    # Cell values are empirical rates from V7.53, clipped to avoid 0/1 certainty.
    # Keys: (slot, round, band), where band is deep (<-60), mid [-60,-40), other (>=-40).
    cell={
        (1,11,"deep"):.0761,(1,11,"mid"):.2500,
        (1,12,"deep"):.9500,(1,12,"mid"):.9500,
        (1,13,"deep"):.0700,
        (1,14,"mid"):.9500,(1,14,"other"):.9500,

        (3,11,"deep"):.1071,(3,11,"mid"):.2667,
        (3,12,"deep"):.6316,(3,12,"mid"):.7500,(3,12,"other"):.0500,
        (3,13,"deep"):.0800,
        (3,14,"mid"):.9500,

        (7,11,"deep"):.5000,(7,11,"mid"):.4167,
        (7,12,"deep"):.2041,(7,12,"other"):.0500,
        (7,13,"deep"):.2700,
        (7,14,"deep"):.9500,

        (12,11,"mid"):.9500,
        (12,12,"deep"):.0500,
        (12,13,"deep"):.9500,(12,13,"mid"):.9500,
        (12,14,"deep"):.9500,
    }

    # Slot-round backoff from V7.53.
    sr={
        (1,11):.0900,(1,12):.9500,(1,13):.0700,(1,14):.9500,
        (3,11):.1313,(3,12):.6300,(3,13):.0800,(3,14):.9500,
        (7,11):.4200,(7,12):.2020,(7,13):.2700,(7,14):.9500,
        (12,11):.9500,(12,12):.0500,(12,13):.9500,(12,14):.9500,
    }

    # Global distance-band backoff from V7.53.
    gb={"deep":.4191,"mid":.8560,"other":.2500}

    d=x-float(next_pick)
    out=np.zeros_like(x,dtype=float)
    for i,val in enumerate(d):
        if not np.isfinite(val):
            out[i]=.50
            continue
        band="deep" if val < -60 else "mid" if val < -40 else "other"
        key=(int(slot),int(round_no),band)
        if key in cell:
            p=cell[key]
        elif (int(slot),int(round_no)) in sr:
            # Blend slot-round backoff with global distance behavior.
            p=.70*sr[(int(slot),int(round_no))]+.30*gb[band]
        else:
            p=gb[band]
        out[i]=float(np.clip(p,.05,.95))
    return out


def execution_choice_with_survival(eval_score, market_pick, current_pick, next_pick, survival):
    """Same V7.50 execution architecture, but supplied a calibrated survival array."""
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    surv=np.asarray(survival,dtype=float)
    reach=np.maximum(mp-float(current_pick),0)
    fall=np.maximum(float(current_pick)-mp,0)
    ready=(fall>=5) | (reach<6) | (surv<.50) | np.isnan(mp)

    n=min(24,len(ev))
    if n<=0:
        return None,ready,surv
    top=np.argpartition(-ev,n-1)[:n] if n<len(ev) else np.arange(len(ev))
    ready_top=top[ready[top]]
    if len(ready_top):
        j=int(ready_top[np.argmax(ev[ready_top]+.035*fall[ready_top])])
        return j,ready,surv

    timing_cost=surv[top]*np.minimum(reach[top],36.0)*.42
    j=int(top[np.argmax(ev[top]-timing_cost)])
    return j,ready,surv


def market_timing_state(market_pick,current_pick,next_pick,randomness=12):
    """Execution state. Player evaluation is handled separately from pick timing."""
    if pd.isna(market_pick):
        return "DRAFT NOW",np.nan
    mp=float(market_pick); cur=float(current_pick)
    surv=survival_probability(mp,next_pick,randomness)
    if cur-mp >= 5:
        return "VALUE FALLER",surv
    reach=mp-cur
    # If we are meaningfully ahead of market and the target is more likely than not
    # to make it back, preserve the target rather than spending this pick early.
    if next_pick is not None and reach>=6 and pd.notna(surv) and surv>=.50:
        return "WAIT / TARGET NEXT PICK",surv
    return "DRAFT NOW",surv


def execution_choice(eval_score, market_pick, current_pick, next_pick, randomness=12):
    """Choose who to draft NOW without changing the underlying player evaluation.

    The model's favorite players remain model targets. Pick execution selects the
    highest-evaluated target whose market window is open. If every good target is a
    WAIT, it chooses the least-cost early pick instead of blindly reaching for #1.
    """
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    surv=survival_probability_array(mp,next_pick,randomness)
    reach=np.maximum(mp-float(current_pick),0)
    fall=np.maximum(float(current_pick)-mp,0)
    ready=(fall>=5) | (reach<6) | (surv<.50) | np.isnan(mp)
    # Only compare realistic model targets, not the full player universe.
    n=min(24,len(ev))
    if n<=0: return None,ready,surv
    top=np.argpartition(-ev,n-1)[:n] if n<len(ev) else np.arange(len(ev))
    ready_top=top[ready[top]]
    if len(ready_top):
        # Evaluation controls the selection among players whose timing window is open.
        j=int(ready_top[np.argmax(ev[ready_top]+.035*fall[ready_top])])
        return j,ready,surv
    # Emergency fallback: all top targets are early. Pay the smallest timing cost
    # while still respecting model evaluation.
    timing_cost=surv[top]*np.minimum(reach[top],36.0)*.42
    j=int(top[np.argmax(ev[top]-timing_cost)])
    return j,ready,surv


def dynamic_faller_threshold(current_pick, teams=12, rounds=15):
    """Round-aware minimum market fall required for a Faller Intercept.

    Early rounds protect elite model conviction.
    Middle rounds become progressively more willing to harvest market value.
    Late rounds aggressively capture model-compatible fallers.
    """
    teams=max(int(teams),1)
    round_no=max(1,int((int(current_pick)-1)//teams)+1)
    if round_no<=3:
        return 14.0, 12, 8.0   # frozen V7.15 early-round rule
    if round_no<=6:
        # V7.16 surgical mid-round discipline: modestly widen the model-compatible
        # band and lower the fall/improvement thresholds without becoming ADP-led.
        return 9.0, 18, 4.0
    if round_no<=10:
        return 8.0, 18, 4.0    # frozen V7.15 R7-10 rule
    # Frozen V7.15 late-round value harvest.
    return 4.0, 28, 2.0


def early_wr_scarcity_choice(eval_score, market_pick, position_code, current_pick, next_pick, normal_choice, teams=12, randomness=12, max_eval_deficit=10.0, max_wr_survival=.52):
    """R1-3 only: scarce market-priority WR intercept; underlying evaluation stays frozen."""
    ev=np.asarray(eval_score,dtype=float); mp=np.asarray(market_pick,dtype=float); pc=np.asarray(position_code,dtype=int)
    normal=int(normal_choice); rnd=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    diag={"wr_scarcity":False,"wr_survival":np.nan,"eval_deficit":np.nan,"market_advantage":np.nan,"wr_index":None}
    if rnd>3 or next_pick is None or len(ev)==0 or pc[normal]==2: return normal,False,diag
    wr=np.flatnonzero(pc==2)
    if not len(wr): return normal,False,diag
    wi=int(wr[np.argmax(ev[wr])]); deficit=float(ev[normal]-ev[wi])
    wmp=float(mp[wi]) if np.isfinite(mp[wi]) else np.nan; nmp=float(mp[normal]) if np.isfinite(mp[normal]) else np.nan
    surv=survival_probability(wmp,next_pick,randomness) if np.isfinite(wmp) else np.nan
    adv=nmp-wmp if np.isfinite(nmp) and np.isfinite(wmp) else np.nan
    diag.update({"wr_survival":surv,"eval_deficit":deficit,"market_advantage":adv,"wr_index":wi})
    if pd.isna(surv) or surv>max_wr_survival or deficit>max_eval_deficit or pd.isna(adv) or adv<0: return normal,False,diag
    diag["wr_scarcity"]=True
    return wi,True,diag


def late_slot_wr_conflict_choice(eval_score, market_pick, position_code, draft_score, vorp,
                                current_pick, next_pick, normal_choice, draft_slot,
                                teams=12, randomness=12, enabled=False,
                                max_eval_deficit=8.0, max_wr_survival=.35,
                                min_draftscore_advantage=.5, require_vorp_driver=True,
                                eligible_slots=(7,12)):
    """R4-6, Picks 7/12 only: diagnostic WR conflict intercept.

    The live champion never calls this with enabled=True. A calibration variant may
    replace an RB/TE normal choice with the best evaluated WR only when:
    - draft slot is 7 or 12
    - round is 4-6
    - normal choice is RB or TE
    - WR is within a controlled FE evaluation deficit
    - WR has low survival probability to next pick
    - selected RB/TE's player/draft-score advantage is positive
    - VORP contribution to that player-score advantage is positive
    """
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    pc=np.asarray(position_code,dtype=int)
    ds=np.asarray(draft_score,dtype=float)
    vp=np.asarray(vorp,dtype=float)
    normal=int(normal_choice)
    rnd=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)

    diag={
        "ls_wr_intercept":False,"wr_index":None,"eval_deficit":np.nan,
        "wr_survival":np.nan,"draftscore_advantage":np.nan,
        "vorp_component_advantage":np.nan
    }
    if (not enabled) or int(draft_slot) not in list(eligible_slots) or rnd<4 or rnd>6:
        return normal,False,diag
    if normal<0 or normal>=len(ev) or pc[normal] not in [1,3]:
        return normal,False,diag

    wr=np.flatnonzero(pc==2)
    if not len(wr):
        return normal,False,diag

    wi=int(wr[np.argmax(ev[wr])])
    deficit=float(ev[normal]-ev[wi])
    wmp=float(mp[wi]) if np.isfinite(mp[wi]) else np.nan
    surv=survival_probability(wmp,next_pick,randomness) if np.isfinite(wmp) else np.nan

    # Exact FE-evaluation contribution from player/draft score.
    ds_adv=.38*float(ds[normal]-ds[wi])
    # VORP is weighted 9x in the frozen champion, then 0.38 in pick evaluation.
    vorp_adv=.38*9.0*float(vp[normal]-vp[wi])

    diag.update({
        "wr_index":wi,"eval_deficit":deficit,"wr_survival":surv,
        "draftscore_advantage":ds_adv,"vorp_component_advantage":vorp_adv
    })

    if pd.isna(surv) or surv>float(max_wr_survival):
        return normal,False,diag
    if deficit>float(max_eval_deficit):
        return normal,False,diag
    if ds_adv<float(min_draftscore_advantage):
        return normal,False,diag
    if require_vorp_driver and vorp_adv<=0:
        return normal,False,diag

    diag["ls_wr_intercept"]=True
    return wi,True,diag


def pick12_faller_activation_snapshot(eval_score, market_pick, position_code, current_pick, next_pick, normal_choice,
                                       randomness=12, min_fall=7.0, max_eval_deficit=8.0,
                                       min_normal_reach=4.0, max_normal_survival=.55):
    ev=np.asarray(eval_score,dtype=float); mp=np.asarray(market_pick,dtype=float); pos=np.asarray(position_code)
    normal=int(normal_choice)
    out={"rbte":False,"reach_pass":False,"faller_exists":False,"eval_pass":False,"survival_pass":False,
         "full_trigger":False,"trigger_no_survival":False,"trigger_no_reach":False,
         "normal_reach":np.nan,"normal_survival":np.nan,"best_faller_amount":np.nan,
         "best_faller_eval_deficit":np.nan,"best_faller_position":"","best_faller_market_pick":np.nan}
    if len(ev)==0 or normal_choice is None: return out
    if int(pos[normal]) not in [1,3]: return out
    out["rbte"]=True
    nr=max(float(mp[normal])-float(current_pick),0.0) if np.isfinite(mp[normal]) else 0.0
    ns=survival_probability(float(mp[normal]),next_pick,randomness) if np.isfinite(mp[normal]) else np.nan
    out["normal_reach"]=nr; out["normal_survival"]=ns
    out["reach_pass"]=bool(nr>=float(min_normal_reach))
    fall=np.maximum(float(current_pick)-mp,0.0)
    raw=np.flatnonzero(np.isfinite(mp) & (fall>=float(min_fall)))
    out["faller_exists"]=bool(len(raw))
    if len(raw):
        # best market faller first, then report whether it is model-compatible
        fi=int(raw[int(np.argmax(fall[raw]))])
        deficit=max(float(ev[normal]-ev[fi]),0.0)
        out["best_faller_amount"]=float(fall[fi])
        out["best_faller_eval_deficit"]=deficit
        out["best_faller_position"]={0:"QB",1:"RB",2:"WR",3:"TE"}.get(int(pos[fi]),str(int(pos[fi])))
        out["best_faller_market_pick"]=float(mp[fi])
        compatible=raw[(float(np.nanmax(ev))-ev[raw])<=float(max_eval_deficit)]
        out["eval_pass"]=bool(len(compatible))
    out["survival_pass"]=bool(pd.notna(ns) and float(ns)<=float(max_normal_survival))
    out["full_trigger"]=bool(out["rbte"] and out["reach_pass"] and out["faller_exists"] and out["eval_pass"] and out["survival_pass"])
    out["trigger_no_survival"]=bool(out["rbte"] and out["reach_pass"] and out["faller_exists"] and out["eval_pass"])
    out["trigger_no_reach"]=bool(out["rbte"] and out["faller_exists"] and out["eval_pass"] and out["survival_pass"])
    return out


def pick12_faller_need_choice(eval_score, market_pick, position_code, current_pick, next_pick, normal_choice,
                              teams=12, randomness=12, enabled=False, min_fall=7.0,
                              max_eval_deficit=8.0, min_normal_reach=4.0, max_normal_survival=.55):
    """Calibration-only Pick-12 R4-6 faller-vs-need execution rule.

    It does not prefer WR by position. It may take the best model-compatible market
    faller before a normal RB/TE reach when the RB/TE still has a reasonable chance
    to survive to the next Pick-12 turn.
    """
    ev=np.asarray(eval_score,dtype=float); mp=np.asarray(market_pick,dtype=float)
    pos=np.asarray(position_code)
    normal=int(normal_choice)
    diag={"trigger":False,"faller_index":None,"faller_amount":0.0,"eval_deficit":np.nan,
          "normal_reach":0.0,"normal_survival":np.nan}
    if not enabled or normal_choice is None or len(ev)==0:
        return normal,False,diag
    rnd=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    if rnd<4 or rnd>6 or int(pos[normal]) not in [1,3]:
        return normal,False,diag

    normal_reach=max(float(mp[normal])-float(current_pick),0.0) if np.isfinite(mp[normal]) else 0.0
    normal_surv=survival_probability(float(mp[normal]),next_pick,randomness) if np.isfinite(mp[normal]) else np.nan
    diag["normal_reach"]=normal_reach; diag["normal_survival"]=normal_surv
    if normal_reach<float(min_normal_reach):
        return normal,False,diag
    if pd.isna(normal_surv) or float(normal_surv)>float(max_normal_survival):
        return normal,False,diag

    fall=np.maximum(float(current_pick)-mp,0.0)
    valid=np.isfinite(mp) & (fall>=float(min_fall))
    if not np.any(valid):
        return normal,False,diag

    # Keep the faller model-compatible; no positional forcing.
    best=float(np.nanmax(ev))
    valid &= (best-ev)<=float(max_eval_deficit)
    cand=np.flatnonzero(valid)
    if not len(cand):
        return normal,False,diag

    # Prioritize open draft-window value, then FE evaluation.
    score=.55*fall[cand] + .45*(ev[cand]-best)
    fi=int(cand[int(np.argmax(score))])
    deficit=max(float(ev[normal]-ev[fi]),0.0)
    diag.update({"faller_index":fi,"faller_amount":float(fall[fi]),"eval_deficit":deficit})
    if fi==normal or deficit>float(max_eval_deficit):
        return normal,False,diag

    diag["trigger"]=True
    return fi,True,diag


def faller_intercept_choice(eval_score, market_pick, current_pick, normal_choice,
                            teams=12, rounds=15, min_fall=None, model_band=None,
                            improvement_required=None):
    """Dynamic, model-compatible market faller override.

    The threshold changes by draft stage rather than using one fixed rule.
    A faller still must remain inside Fantasy Edge's model-compatible target band.
    """
    ev=np.asarray(eval_score,dtype=float)
    mp=np.asarray(market_pick,dtype=float)
    if len(ev)==0 or normal_choice is None:
        return normal_choice,False,0.0

    auto_min,auto_band,auto_improve=dynamic_faller_threshold(current_pick,teams,rounds)
    min_fall=float(auto_min if min_fall is None else min_fall)
    model_band=int(auto_band if model_band is None else model_band)
    improvement_required=float(auto_improve if improvement_required is None else improvement_required)

    fall=np.maximum(float(current_pick)-mp,0)
    valid=np.isfinite(mp) & (fall>=min_fall)
    normal=int(normal_choice)
    normal_fall=float(fall[normal]) if np.isfinite(fall[normal]) else 0.0

    if not np.any(valid):
        return normal,False,normal_fall

    n=min(model_band,len(ev))
    top=np.argpartition(-ev,n-1)[:n] if n<len(ev) else np.arange(len(ev))
    cand=top[valid[top]]
    if len(cand)==0:
        return normal,False,normal_fall

    # Model compatibility remains important, but larger fallers gain increasingly
    # more weight instead of all fallers above the minimum being treated similarly.
    ev_top=ev[top]
    spread=max(float(np.nanstd(ev_top)),1.0)
    best_eval=float(np.nanmax(ev_top))
    compatibility=(ev[cand]-best_eval)/spread

    excess=np.maximum(fall[cand]-min_fall,0)
    round_no=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    if round_no>=11:
        # Frozen V7.15 late-round harvest scoring.
        fall_value=.46*fall[cand] + .055*(excess**1.40)
        intercept_score=fall_value + 1.45*compatibility
    elif 4<=round_no<=6:
        # V7.16: modest mid-round value boost, still keeping model compatibility
        # stronger than in late rounds.
        fall_value=.36*fall[cand] + .040*(excess**1.35)
        intercept_score=fall_value + 1.85*compatibility
    else:
        # Frozen V7.15 behavior for R1-3 and R7-10.
        fall_value=.32*fall[cand] + .035*(excess**1.35)
        intercept_score=fall_value + 2.0*compatibility
    best_cand=int(cand[int(np.argmax(intercept_score))])

    # Require the faller to improve market value enough over the normal execution
    # choice for the current draft stage.
    round_no=max(1,int((int(current_pick)-1)//max(int(teams),1))+1)
    if round_no>=11:
        normal_reach=max(float(mp[normal])-float(current_pick),0) if np.isfinite(mp[normal]) else 0.0
        required=max(min_fall,normal_fall+improvement_required)
        # Frozen V7.15 late-round anti-reach safeguard.
        if normal_reach>=4.0:
            required=min_fall
        if float(fall[best_cand]) >= required:
            return best_cand,True,float(fall[best_cand])
    elif 4<=round_no<=6:
        # V7.16 mid-round anti-reach safeguard: weaker than late rounds.
        # If the normal choice is a 6+ pick reach and a model-compatible 9+ pick
        # faller exists, the faller only needs to clear the normal R4-6 threshold.
        normal_reach=max(float(mp[normal])-float(current_pick),0) if np.isfinite(mp[normal]) else 0.0
        required=max(min_fall,normal_fall+improvement_required)
        if normal_reach>=6.0:
            required=min_fall
        if float(fall[best_cand]) >= required:
            return best_cand,True,float(fall[best_cand])
    else:
        # Frozen V7.15 behavior for R1-3 and R7-10.
        if float(fall[best_cand]) >= max(min_fall,normal_fall+improvement_required):
            return best_cand,True,float(fall[best_cand])
    return normal,False,normal_fall
def roster_need_for_mock(roster_df, pos, slots):
    """Marginal roster value: each additional player is worth less once usable depth is filled."""
    counts=roster_df.position.value_counts().to_dict() if len(roster_df) else {}
    have=int(counts.get(pos,0))
    direct=max(int(slots.get(pos,0))-have,0)
    flex_used=max(0,sum(counts.get(p,0) for p in ["RB","WR","TE"])-
                    sum(int(slots.get(p,0)) for p in ["RB","WR","TE"]))
    flex_need=max(int(slots.get("FLEX",0))-flex_used,0)

    if direct>0:
        base=11.0+min(direct,2)*2.0
        if pos=="WR": base+=2.0
        return base

    if pos=="WR":
        if flex_need>0: return 8.0
        if have==2: return 6.0
        if have==3: return 4.0
        if have==4: return 0.5
        return -5.0
    if pos=="RB":
        if flex_need>0 and have<3: return 5.0
        if have==2: return 3.0
        if have==3: return 0.5
        if have==4: return -3.5
        return -10.0
    if pos=="TE": return -10.0 if have>=1 else 0.0
    if pos=="QB": return -14.0 if have>=1 else 0.0
    if pos in ["DL","DB"]:
        return -12.0 if have>=int(slots.get(pos,1)) else -1.0
    return -3.0

def _small_roster_utility_df(roster, slots):
    """Expected final-roster utility for a small drafted roster DataFrame.

    Starters receive full value, FLEX receives near-starter value, and bench players
    receive diminishing insurance/upside value. This evaluates the players actually
    on the roster rather than prescribing a fixed QB/RB/WR/TE bench recipe.
    """
    if roster is None or len(roster)==0:
        return 0.0
    r=roster.copy()
    r["_base_value"]=r["projection"].fillna(0)+0.70*r["vorp"].fillna(0).clip(lower=-5)
    used=set(); total=0.0
    # Required position starters.
    for pos in ["QB","RB","WR","TE","DL","DB"]:
        n=max(int(slots.get(pos,0)),0)
        px=r[r.position.eq(pos)].sort_values("_base_value",ascending=False)
        for idx,row in px.head(n).iterrows():
            used.add(idx)
            total += float(row.projection)*1.00 + float(row.vorp)*0.90
    # FLEX from remaining RB/WR/TE.
    flex_n=max(int(slots.get("FLEX",0)),0)
    flex=r[(~r.index.isin(used)) & r.position.isin(["RB","WR","TE"])].sort_values("_base_value",ascending=False)
    for idx,row in flex.head(flex_n).iterrows():
        used.add(idx)
        total += float(row.projection)*0.92 + float(row.vorp)*0.75
    # Bench: value depends on actual player quality with diminishing depth utility.
    bench=r[~r.index.isin(used)].sort_values("_base_value",ascending=False)
    depth={"QB":0,"RB":0,"WR":0,"TE":0,"DL":0,"DB":0}
    bench_mult={"QB":[.14,.03],"RB":[.25,.15,.08,.03],"WR":[.40,.30,.20,.11,.06],
                "TE":[.16,.04],"DL":[.06],"DB":[.06]}
    for _,row in bench.iterrows():
        p=row.position; d=depth.get(p,0); arr=bench_mult.get(p,[.05])
        mult=arr[d] if d<len(arr) else .02
        total += mult*(float(row.projection)+0.55*max(float(row.vorp),0))
        depth[p]=d+1
    return float(total)


def _candidate_roster_delta_df(roster, candidates, slots, exact_cap=72):
    """Fast V7.3 marginal roster utility with bounded exact evaluation."""
    if candidates is None or len(candidates)==0:
        return np.array([],dtype=float)
    current=_small_roster_utility_df(roster,slots)
    c=candidates
    proj=pd.to_numeric(c["projection"],errors="coerce").fillna(0).to_numpy(float)
    vorp=pd.to_numeric(c["vorp"],errors="coerce").fillna(0).to_numpy(float)
    ds=pd.to_numeric(c["draft_score"],errors="coerce").fillna(-1e9).to_numpy(float)
    cr=pd.to_numeric(c["consensus_rank"],errors="coerce").fillna(999).to_numpy(float)
    approx=.10*proj+.08*np.maximum(vorp,0)
    out=approx.copy()
    n=min(int(exact_cap),len(c))
    k1=max(1,n//3); k2=max(1,n//3)
    a=np.argpartition(-ds,min(k1-1,len(ds)-1))[:k1]
    b=np.argpartition(cr,min(k2-1,len(cr)-1))[:k2]
    pi=[]; posarr=c["position"].astype(str).to_numpy()
    per=max(2,n//18)
    for pname in ["QB","RB","WR","TE","DL","DB"]:
        loc=np.flatnonzero(posarr==pname)
        if loc.size:
            take=min(per,loc.size)
            best=loc[np.argpartition(-ds[loc],min(take-1,loc.size-1))[:take]]
            pi.extend(best.tolist())
    short=np.unique(np.concatenate([a,b,np.asarray(pi,dtype=int)]))
    if len(short)>n:
        composite=(-ds[short])+0.05*cr[short]
        short=short[np.argsort(composite)[:n]]
    for j in short:
        row=c.iloc[int(j)]
        temp=pd.concat([roster,row.to_frame().T],ignore_index=True) if len(roster) else row.to_frame().T
        out[int(j)]=_small_roster_utility_df(temp,slots)-current
    return out
def _minimum_required_picks_remaining(counts, slots):
    """Minimum picks needed to complete fixed starters plus FLEX."""
    fixed_positions=["QB","RB","WR","TE","K","DL","DB"]
    fixed_def={p:max(int(slots.get(p,0))-int(counts.get(p,0)),0) for p in fixed_positions}

    required_skill=(
        int(slots.get("RB",0))+int(slots.get("WR",0))+int(slots.get("TE",0))+
        int(slots.get("FLEX",0))
    )
    have_skill=int(counts.get("RB",0))+int(counts.get("WR",0))+int(counts.get("TE",0))
    fixed_skill_def=fixed_def["RB"]+fixed_def["WR"]+fixed_def["TE"]
    flex_extra=max(required_skill-have_skill-fixed_skill_def,0)
    return int(sum(fixed_def.values())+flex_extra), fixed_def, int(flex_extra)


def _candidate_keeps_roster_feasible(roster, candidate_pos, round_no, rounds, slots):
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    after=dict(counts)
    after[candidate_pos]=int(after.get(candidate_pos,0))+1
    remaining_after=max(int(rounds)-int(round_no),0)
    minimum_after,_,_=_minimum_required_picks_remaining(after,slots)
    return minimum_after<=remaining_after


def draft_eligibility(avail, roster, round_no, rounds, slots):
    """Hard legality plus mathematical end-of-draft roster feasibility."""
    a=avail.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}

    qb=int(counts.get("QB",0)); te=int(counts.get("TE",0))
    dl=int(counts.get("DL",0)); db=int(counts.get("DB",0)); k=int(counts.get("K",0))
    total_idp=dl+db

    # Required-position depletion guard. If an unfilled required position is down
    # to two available players, take that requirement now rather than risk a
    # mathematically legal but practically impossible late roster.
    _required_open=[
        p for p in ["QB","RB","WR","TE","K","DL","DB"]
        if int(counts.get(p,0)) < int(slots.get(p,0))
    ]
    _critical=[]
    for _p in _required_open:
        _n=int((a["position"].astype(str)==_p).sum())
        if 0 < _n <= 2:
            _critical.append((_n,_p))
    if _critical:
        _critical.sort()
        _critical_pos=_critical[0][1]
        _critical_pool=a[a["position"].astype(str).eq(_critical_pos)]
        if len(_critical_pool):
            a=_critical_pool.copy()

    # Allow normal depth, including exactly one extra impact IDP.
    if int(slots.get("QB",1))<=1 and qb>=2:
        a=a[~a.position.eq("QB")]
    if int(slots.get("TE",1))<=1 and te>=2:
        a=a[~a.position.eq("TE")]
    if dl>=2:
        a=a[~a.position.eq("DL")]
    if db>=2:
        a=a[~a.position.eq("DB")]
    # Required starters are 1 DL + 1 DB. Allow at most ONE extra impact defender.
    if total_idp>=3:
        a=a[~a.position.isin(["DL","DB"])]
    if k>=max(int(slots.get("K",1)),1):
        a=a[~a.position.eq("K")]

    # V6.38: Never hard-hide required IDP positions from Live/Mock candidate pools.
    # Older builds removed every DL/DB through round 7 whenever enough offensive
    # players remained. That made the Position=DB/DL tables appear empty and
    # prevented the engine from considering an elite defender. Early-IDP timing
    # is already handled by the scoring/opportunity penalties downstream, so keep
    # defenders visible and let the model rank them rather than deleting them.

    # Candidate-level feasibility. A pick is illegal if it leaves too few future
    # picks to finish all required starters and both FLEX slots.
    if len(a):
        feasible=a["position"].map(
            lambda p:_candidate_keeps_roster_feasible(
                roster,str(p),int(round_no),int(rounds),slots
            )
        )
        a=a[feasible].copy()

    # Exact completion boundary: only a pick that reduces the minimum remaining
    # requirement may be selected.
    minimum_now,_,_=_minimum_required_picks_remaining(counts,slots)
    picks_left=int(rounds)-int(round_no)+1
    if len(a) and minimum_now>0 and picks_left<=minimum_now:
        reducers=[]
        for ix,row in a.iterrows():
            after=dict(counts)
            p=str(row.position)
            after[p]=int(after.get(p,0))+1
            after_min,_,_=_minimum_required_picks_remaining(after,slots)
            if after_min<minimum_now:
                reducers.append(ix)
        # Exact completion boundary: if no candidate reduces the remaining requirement,
        # there is no legal candidate.
        a=a.loc[reducers].copy()

    # Late-bench diversification authority.
    # Once the core offense is deep (5 RB + 5 WR) and required starters are covered,
    # reserve a remaining bench opportunity for a qualifying impact DL/DB.
    counts_now=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    core_filled=(
        int(counts_now.get("QB",0))>=int(slots.get("QB",1)) and
        int(counts_now.get("RB",0))>=int(slots.get("RB",2)) and
        int(counts_now.get("WR",0))>=int(slots.get("WR",2)) and
        int(counts_now.get("TE",0))>=int(slots.get("TE",1)) and
        int(counts_now.get("DL",0))>=int(slots.get("DL",1)) and
        int(counts_now.get("DB",0))>=int(slots.get("DB",1))
    )
    deep_offense=(int(counts_now.get("RB",0))>=5 and int(counts_now.get("WR",0))>=5)
    total_idp=int(counts_now.get("DL",0))+int(counts_now.get("DB",0))
    if core_filled and deep_offense and total_idp<3 and len(a):
        # Do not hard-force a defender here; scorer will require actual impact quality.
        # But prevent both RB6 and WR6 from consuming the final diversification window.
        picks_left=int(rounds)-int(round_no)+1
        if picks_left<=3:
            a=a[~((a.position.eq("RB")) | (a.position.eq("WR")))].copy() if a.position.isin(["DL","DB"]).any() else a

    # If all required starters/FLEX are already complete, soft depth/saturation
    # rules are not allowed to create an empty candidate set. Rebuild from the
    # original available pool using only true roster hard caps.
    if len(a)==0:
        minimum_now,_,_=_minimum_required_picks_remaining(counts,slots)
        if minimum_now==0:
            a=avail.copy()
            if int(slots.get("QB",1))<=1 and qb>=2:
                a=a[~a.position.eq("QB")]
            if int(slots.get("TE",1))<=1 and te>=2:
                a=a[~a.position.eq("TE")]
            if total_idp>=3:
                a=a[~a.position.isin(["DL","DB"])]
            if k>=max(int(slots.get("K",1)),1):
                a=a[~a.position.eq("K")]

    return a


def grade_mock(roster, teams, slots):
    def _gnum(name, default=0.0):
        if name in roster.columns:
            return pd.to_numeric(roster[name],errors="coerce").fillna(float(default))
        return pd.Series(float(default),index=roster.index,dtype=float)
    """Grade the mock on *realized* draft advantage, not a cosmetic score boost.

    v9.42 changes:
    - Honors the exact league: 1 TE is required; FLEX may also use RB/WR/TE.
    - Model Edge measures what the draft actually captured: market value at cost, model conviction
      at cost, VORP/projection quality, and roster construction.
    - DL/DB rows with obviously non-comparable global model ranks no longer poison Model Edge;
      shallow-IDP quality is judged by projection/market support and the shared IDP authority layer.
    - Reaches are penalized asymmetrically; falling past market is rewarded but capped so one late
      pick cannot inflate the entire grade.
    """
    if roster is None or len(roster)==0:
        return {"score":0,"grade":"F","starter":0,"value":0,"penalty":100,
                "draft_value":0,"construction":0,"positional_advantage":0,
                "model_edge_score":0,"opportunity_penalty":0}

    r=roster.copy()
    for c in ["projection","vorp","model_rank","consensus_rank","mock_pick"]:
        if c in r.columns: r[c]=pd.to_numeric(r[c],errors="coerce")
    counts=r.position.value_counts().to_dict()

    # Exact required starters: TE is required in this league.
    req={p:max(int(slots.get(p,d)),0) for p,d in
         {"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DL":1,"DB":1}.items()}
    flex_n=max(int(slots.get("FLEX",0)),0)

    # Realized market value: positive means we drafted the player AFTER consensus cost.
    # Reaches hurt faster than fallers help; both are capped for robustness.
    if "mock_pick" in r.columns:
        market_delta=r.mock_pick-r.consensus_rank
    else:
        market_delta=r.consensus_rank-r.model_rank
    market_delta=market_delta.where(r.consensus_rank.notna())
    market_points=np.where(market_delta.notna(),
        np.where(market_delta>=0, np.minimum(market_delta,36.0)*0.42,
                 np.maximum(market_delta,-30.0)*0.62), 0.0)

    # Model conviction realized at cost. Global offensive ranks are useful here, but the legacy
    # DL/DB global rank scale is not comparable (e.g. quality IDPs can be rank 500+ / 2000+).
    # For IDP, use market-supported positional quality rather than that broken cross-position rank.
    model_delta=(r.mock_pick-r.model_rank) if "mock_pick" in r.columns else (r.consensus_rank-r.model_rank)
    is_idp=r.position.isin(["DL","DB"])
    valid_model=(~is_idp) & r.model_rank.notna() & (r.model_rank<400)
    conviction=np.zeros(len(r),dtype=float)
    md=model_delta.to_numpy(dtype=float)
    vm=valid_model.to_numpy(dtype=bool)
    conviction[vm]=np.where(md[vm]>=0,np.minimum(md[vm],42.0)*0.24,np.maximum(md[vm],-35.0)*0.34)

    # Player-quality support: VORP is the primary cross-position signal. Projection adds a small
    # within-roster quality signal; IDP zero-VORP is neutral rather than an automatic failure.
    vorp=r.vorp.fillna(0).clip(-3,12)

    # Use roster-adjusted usable VORP when available so RB6/WR6/QB2 do not inflate Model Edge.
    if "usable_vorp" in r.columns:
        usable_vorp=pd.to_numeric(r["usable_vorp"],errors="coerce").fillna(vorp).clip(-3,12)
    else:
        usable_vorp=vorp
    vorp_points=(usable_vorp*0.72).to_numpy(dtype=float)
    proj=r.projection.fillna(0)
    quality=np.zeros(len(r),dtype=float)
    off=(~is_idp).to_numpy(dtype=bool)
    quality[off]=np.clip((proj.to_numpy(dtype=float)[off]-10.0)*0.12,-1.0,1.6)
    # Shallow IDP: reward credible market support + usable projection, without inventing VORP.
    idpm=is_idp.to_numpy(dtype=bool)
    cr=r.consensus_rank.to_numpy(dtype=float)
    pr=proj.to_numpy(dtype=float)
    quality[idpm]=np.where(np.isfinite(cr[idpm]),np.clip((130.0-cr[idpm])/55.0,-1.0,1.4),-0.5)
    quality[idpm]+=np.clip((pr[idpm]-5.0)*0.35,-0.5,1.0)

    pick_edge=market_points+conviction+vorp_points+quality
    avg_pick_edge=float(np.nanmean(pick_edge)) if len(pick_edge) else 0.0

    # Fantasy Edge calibration:
    # 100/100 is achievable, but only through repeated quality decisions rather than
    # a cosmetic score boost. Reward consistency across the whole roster.
    _clean_pick=((market_delta.fillna(-999)>=-5) & (vorp>=0)).astype(float)
    _clean_rate=float(_clean_pick.mean()) if len(_clean_pick) else 0.0
    _value_rate=float((market_delta.fillna(-999)>=0).mean()) if len(r) else 0.0

    # Base edge comes from realized per-pick advantage. Consistency adds at most 4 points:
    # 2.5 for avoiding bad-value/negative-VORP picks and 1.5 for repeatedly beating market.
    _consistency_bonus=2.5*_clean_rate + 1.5*_value_rate
    model_edge=float(np.clip(58.0+2.15*avg_pick_edge+_consistency_bonus,35,100))

    # Draft value is primarily realized market value + VORP, not model-vs-market disagreement.
    avg_market=float(np.nanmean(np.clip(market_delta.fillna(0),-30,36))) if len(r) else 0.0
    avg_vorp=float(usable_vorp.mean()) if len(r) else 0.0
    draft_value=float(np.clip(62+0.62*avg_market+2.0*avg_vorp,35,100))
    # Realized pick economics: Draft Value should respond to the actual roster,
    # not remain almost static across simulations.
    _rv=_gnum("vorp",0.0)
    _rp=_gnum("projection",0.0)
    if "roster_opportunity" in roster.columns:
        _ro=pd.to_numeric(roster["roster_opportunity"],errors="coerce").fillna(0.0)
    elif "roster_opportunity_adj" in roster.columns:
        _ro=pd.to_numeric(roster["roster_opportunity_adj"],errors="coerce").fillna(0.0)
    else:
        _ro=pd.Series(0.0,index=roster.index,dtype=float)
    realized_pick_economics=float(np.clip(
        0.55*np.nanmean(np.clip(_rv,-10,35))+
        0.035*np.nanmean(np.clip(_rp,0,400))+
        0.30*np.nanmean(np.clip(_ro,-10,15)),
        -5,12
    ))
    draft_value=float(np.clip(draft_value+realized_pick_economics,0,100))
    # V6.16: preserve the legacy market-timing-only value for transparency.
    raw_market_draft_value=float(draft_value)

    construction=100.0
    for p,v in req.items():
        construction-=16*max(v-counts.get(p,0),0)
    # FLEX is filled by the best remaining RB/WR/TE after nominal RB/WR/TE starters.
    skill=r[r.position.isin(["RB","WR","TE"])].copy()
    nominal=req["RB"]+req["WR"]+req["TE"]
    flex_available=max(len(skill)-nominal,0)
    construction-=14*max(flex_n-flex_available,0)
    # Healthy depth targets for this exact six-bench build with one required TE.
    rb,wr=counts.get("RB",0),counts.get("WR",0)
    if rb+wr+counts.get("TE",0)<6: construction-=5*(6-(rb+wr+counts.get("TE",0)))
    qb,te,dl,db=[counts.get(p,0) for p in ["QB","TE","DL","DB"]]
    construction-=12*max(qb-2,0)+10*max(te-2,0)
    # V6.11: one merit-earned backup IDP is legal bench construction. Penalize
    # only a fourth defender or excessive same-position defensive depth.
    _idp_total=dl+db
    construction-=7*max(_idp_total-3,0)
    construction-=4*max(dl-2,0)+4*max(db-2,0)
    construction=float(np.clip(construction,0,100))

    # Starter VORP: exact positional starters, then FLEX from remaining RB/WR/TE.
    starter=0.0; used=set()
    for p in ["QB","RB","WR","TE","K","DL","DB"]:
        n=req[p]
        if n<=0: continue
        idx=r[r.position.eq(p)].vorp.nlargest(n).index
        used.update(idx.tolist()); starter+=float(r.loc[idx,"vorp"].sum())
    flex_pool=r.loc[~r.index.isin(used) & r.position.isin(["RB","WR","TE"]),"vorp"]
    starter+=float(flex_pool.nlargest(flex_n).sum())
    positional=float(np.clip(50+starter*.78,35,100))

    # Opportunity cost: redundant depth, unnecessary early QB2/TE2, and
    # contextually avoidable reaches. Raw ADP reach cost is retained separately
    # so the dashboard remains transparent.
    opp=0.0; raw_opp=0.0; seen={"QB":0,"TE":0}
    ordered=r.sort_values("mock_pick") if "mock_pick" in r.columns else r
    for _idx,row in ordered.iterrows():
        p=row.position
        if p in seen:
            seen[p]+=1
            if seen[p]>=2 and float(row.get("mock_pick",999))<120:
                opp+=4; raw_opp+=4
        crv=row.get("consensus_rank",np.nan); pk=row.get("mock_pick",np.nan)
        if pd.notna(crv) and pd.notna(pk):
            reach=float(crv)-float(pk)  # positive = drafted ahead of market
            if reach>18:
                _reach_cost=min(8,(reach-18)*.12)
                raw_opp+=_reach_cost
                _avoidable=bool(row.get("avoidable_reach",True))
                if _avoidable:
                    opp+=_reach_cost

    # Portfolio/reach diagnostics. Contextual rate drives decision-quality
    # penalty; raw rate is reported separately.
    _reach_series=(r.consensus_rank-r.mock_pick) if "mock_pick" in r.columns else pd.Series(0,index=r.index)
    _raw_big_reach_rate=float((_reach_series>24).mean()) if len(r) else 0.0
    if "avoidable_reach" in r.columns:
        _avoid_flag=r["avoidable_reach"].fillna(False).astype(bool)
        _big_reach_rate=float(((_reach_series>24) & _avoid_flag).mean()) if len(r) else 0.0
    else:
        _big_reach_rate=_raw_big_reach_rate
    _redundant_depth=max(counts.get("RB",0)-5,0)+max(counts.get("WR",0)-5,0)+max(counts.get("QB",0)-2,0)+max(counts.get("TE",0)-2,0)
    _double_backup=int(counts.get("QB",0)>=2 and counts.get("TE",0)>=2)
    _portfolio_penalty=min(10.0,3.5*_redundant_depth + 2.5*_double_backup)
    _reach_penalty=min(8.0,12.0*_big_reach_rate)

    _idp_total=int(counts.get("DL",0))+int(counts.get("DB",0))
    _diversification_penalty=0.0
    if counts.get("RB",0)>=6 and counts.get("WR",0)>=6 and _idp_total<=2:
        _diversification_penalty=6.0

    opp+=_portfolio_penalty+_reach_penalty+_diversification_penalty
    raw_opp+=_portfolio_penalty+min(8.0,12.0*_raw_big_reach_rate)+_diversification_penalty

    # V6.16 calibrated Draft Value: draft capital is still the majority signal,
    # but a draft is also valuable when that capital converts into starter advantage,
    # usable bench upside, and low opportunity waste. Keep raw_market_draft_value
    # alongside this score so the dashboard cannot hide pure ADP efficiency.
    _bench_value_score=float(np.clip(70.0+2.0*float(np.clip(
        r.loc[~r.index.isin(used),"vorp"].fillna(0).clip(-2,10).sum(),-10,15
    )),35,100))
    _capital_efficiency=float(np.clip(100.0-5.0*float(opp),0,100))
    draft_value=float(np.clip(
        0.70*raw_market_draft_value +
        0.15*positional +
        0.10*_bench_value_score +
        0.05*_capital_efficiency,
        0,100
    ))

    # Interpretable quality composite.
    model_edge=float(np.clip(
        0.42*draft_value +
        0.30*construction +
        0.20*positional +
        8.0*_clean_rate -
        0.45*float(opp),
        0,100
    ))

    # Overall grade uses the same economics without double-counting opportunity loss.
    score=float(np.clip(.34*draft_value+.30*construction+.22*positional+.14*model_edge-0.35*opp,0,100))
    _construction_edge_penalty=0.0
    _draft_value_edge_penalty=0.0
    _positional_edge_penalty=0.0
    _opportunity_edge_penalty=0.0
    grade="A+" if score>=94 else "A" if score>=90 else "A-" if score>=86 else "B+" if score>=82 else "B" if score>=78 else "B-" if score>=74 else "C+" if score>=70 else "C" if score>=65 else "C-" if score>=60 else "D" if score>=55 else "F"
    return {"score":score,"grade":grade,"starter":starter,"value":avg_market,"penalty":max(0,100-construction),
            "draft_value":draft_value,"raw_market_draft_value":raw_market_draft_value,
            "construction":construction,"positional_advantage":positional,
            "model_edge_score":model_edge,"opportunity_penalty":opp,
            "raw_opportunity_penalty":raw_opp,"starter_vorp":starter,
            "clean_pick_rate":_clean_rate,"market_win_rate":_value_rate,
            "big_reach_rate":_big_reach_rate,"raw_big_reach_rate":_raw_big_reach_rate,"portfolio_penalty":_portfolio_penalty,"diversification_penalty":_diversification_penalty,"construction_edge_penalty":_construction_edge_penalty,"draft_value_edge_penalty":_draft_value_edge_penalty,"positional_edge_penalty":_positional_edge_penalty,"opportunity_edge_penalty":_opportunity_edge_penalty}

def _injury_severity(status):
    x=str(status or "").strip().lower()
    if x in ["ir","pup","nfi","reserve/ir","reserve/pup"]: return 3
    if x in ["out","suspended","susp"]: return 2
    if x in ["doubtful","questionable","q","d"]: return 1
    return 0



def _v677_normalize_injury_status(status):
    """One injury/status vocabulary used across every Fantasy Edge tab."""
    x=str(status or "").strip().upper()
    if x in ("", "NONE", "NAN", "HEALTHY", "ACTIVE", "FULL", "FULL PARTICIPATION"):
        return "ACTIVE"
    if x in ("Q", "QUESTIONABLE"):
        return "QUESTIONABLE"
    if x in ("D", "DOUBTFUL"):
        return "DOUBTFUL"
    if x in ("O", "OUT"):
        return "OUT"
    if x in ("IR", "RESERVE/IR", "INJURED RESERVE"):
        return "IR"
    if x in ("PUP", "RESERVE/PUP", "PHYSICALLY UNABLE TO PERFORM"):
        return "PUP"
    if x in ("NFI", "RESERVE/NFI"):
        return "NFI"
    if x in ("SUSP", "SUSPENDED"):
        return "SUSPENDED"
    if x in ("DNR", "DO NOT DRAFT", "AVOID"):
        return "DO NOT DRAFT"
    # Keep unexpected official designations visible instead of silently discarding them.
    return x

def _v677_status_icon(status):
    s=_v677_normalize_injury_status(status)
    return {
        "ACTIVE":"🟢 ACTIVE",
        "QUESTIONABLE":"🟡 QUESTIONABLE",
        "DOUBTFUL":"🟠 DOUBTFUL",
        "OUT":"🔴 OUT",
        "IR":"⛔ IR",
        "PUP":"⛔ PUP",
        "NFI":"⛔ NFI",
        "SUSPENDED":"⛔ SUSPENDED",
        "DO NOT DRAFT":"⛔ DO NOT DRAFT",
    }.get(s, "⚪ "+s)




# ---------------- V6.81 direct Sleeper injury-field integration ----------------
@st.cache_data(ttl=900, show_spinner=False)
def _v681_sleeper_injury_watch():
    """
    Read Sleeper's actual injury-specific player fields directly.
    This fixes V6.80's main gap: the production board often had a blank/stale
    injury column, so QUESTIONABLE/LIMITED players were being normalized to ACTIVE.
    """
    out={}
    try:
        players=sleeper_players()
        if not isinstance(players,dict):
            return out

        for pid,pl in players.items():
            if not isinstance(pl,dict):
                continue
            name=str(
                pl.get("full_name")
                or " ".join([str(pl.get("first_name") or ""),str(pl.get("last_name") or "")]).strip()
                or ""
            ).strip()
            if not name:
                continue

            injury_status=str(pl.get("injury_status") or "").strip()
            generic_status=str(pl.get("status") or "").strip()
            practice=str(
                pl.get("practice_participation")
                or pl.get("practice_status")
                or ""
            ).strip()
            body=str(
                pl.get("injury_body_part")
                or pl.get("body_part")
                or pl.get("injury_notes")
                or ""
            ).strip()
            injury_start=str(pl.get("injury_start_date") or "").strip()

            # Game designation first.
            raw=(injury_status + " | " + generic_status).upper()
            designation="ACTIVE"
            if "PHYSICALLY UNABLE" in raw or re.search(r"\bPUP\b",raw):
                designation="PUP"
            elif "NON-FOOTBALL" in raw or re.search(r"\bNFI\b",raw):
                designation="NFI"
            elif "INJURED RESERVE" in raw or "RESERVE/INJURED" in raw or re.search(r"\bIR\b",raw):
                designation="IR"
            elif "SUSPEND" in raw:
                designation="SUSPENDED"
            elif "OUT" in raw:
                designation="OUT"
            elif "DOUBTFUL" in raw:
                designation="DOUBTFUL"
            elif "QUESTIONABLE" in raw or injury_status.upper()=="Q":
                designation="QUESTIONABLE"

            # Sleeper commonly has practice text even when no final game designation exists.
            p=practice.upper()
            practice_norm=""
            if "DID NOT PARTICIPATE" in p or p=="DNP":
                practice_norm="DNP"
            elif "LIMIT" in p:
                practice_norm="Limited"
            elif "FULL" in p:
                practice_norm="Full"
            elif practice:
                practice_norm=practice

            # Only store records with real injury/practice/reserve information.
            if designation!="ACTIVE" or practice_norm or body or injury_start:
                out[_owner_key(name)]={
                    "status":designation,
                    "practice":practice_norm,
                    "injury":body,
                    "updated":injury_start,
                    "team":str(pl.get("team") or "").upper(),
                    "source":"Fantasy Edge Injury Watch (Sleeper live fields)",
                    "raw_injury_status":injury_status,
                    "raw_player_status":generic_status,
                    "player_id":str(pid),
                    "player":name,
                    "practice_source":"Sleeper live fields" if practice_norm else "",
                }
    except Exception as e:
        pass  # cached loaders must not mutate session_state
    return out

# ---------------- V6.80 Fantasy Edge Injury Watch intelligence ----------------
# Adds richer weekly injury-report information (game designation, practice status,
# injury/body part, update date) across the entire player pool.
@st.cache_data(ttl=900, show_spinner=False)
def _v680_espn_injury_watch_feed():
    """
    Returns canonical-name keyed injury intelligence for the full NFL player pool.
    ESPN team injury endpoints are used for current weekly designations/practice
    detail. Reserve-list authority remains a separate higher-priority layer.
    """
    out={}
    try:
        teams_url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=40"
        tr=requests.get(teams_url,timeout=8,headers={"User-Agent":"Mozilla/5.0"})
        tr.raise_for_status()
        sports=tr.json().get("sports") or []
        leagues=(sports[0].get("leagues") or []) if sports else []
        teams=(leagues[0].get("teams") or []) if leagues else []

        for tw in teams:
            team=(tw.get("team") or {})
            team_id=str(team.get("id") or "").strip()
            abbr=str(team.get("abbreviation") or "").upper().strip()
            slug=str(team.get("slug") or "").strip()
            if not team_id and not slug:
                continue

            urls=[]
            if team_id:
                urls.append(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{team_id}/injuries")
            if slug:
                urls.append(f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{slug}/injuries")

            data=None
            for url in urls:
                try:
                    rr=requests.get(url,timeout=6,headers={"User-Agent":"Mozilla/5.0"})
                    if rr.status_code==200:
                        data=rr.json()
                        break
                except Exception:
                    continue
            if not isinstance(data,dict):
                continue

            # ESPN has used several shapes over time. Walk plausible collections.
            candidates=[]
            for key in ["injuries","items","athletes"]:
                val=data.get(key)
                if isinstance(val,list):
                    candidates.extend(val)

            # Some responses group entries.
            for grp in data.get("groups",[]) or []:
                if isinstance(grp,dict):
                    for key in ["injuries","items","athletes"]:
                        val=grp.get(key)
                        if isinstance(val,list):
                            candidates.extend(val)

            def _flatten_entry(entry):
                if not isinstance(entry,dict):
                    return []
                # group wrapper
                for key in ["items","athletes","injuries"]:
                    if isinstance(entry.get(key),list):
                        return entry.get(key)
                return [entry]

            flat=[]
            for entry in candidates:
                flat.extend(_flatten_entry(entry))

            for item in flat:
                if not isinstance(item,dict):
                    continue
                athlete=item.get("athlete") if isinstance(item.get("athlete"),dict) else item
                name=str(
                    athlete.get("fullName")
                    or athlete.get("displayName")
                    or item.get("fullName")
                    or item.get("displayName")
                    or ""
                ).strip()
                if not name:
                    continue

                # Gather status text from common ESPN fields.
                status_obj=item.get("status") or athlete.get("status") or {}
                status_texts=[]
                if isinstance(status_obj,dict):
                    status_texts.extend([
                        status_obj.get("name"), status_obj.get("type"),
                        status_obj.get("description"), status_obj.get("abbreviation"),
                        status_obj.get("detail"), status_obj.get("shortDetail")
                    ])
                elif status_obj:
                    status_texts.append(status_obj)

                status_texts.extend([
                    item.get("type"), item.get("status"),
                    item.get("designation"), item.get("gameStatus"),
                    item.get("shortComment"), item.get("longComment"),
                    item.get("details")
                ])
                status_raw=" | ".join(str(x) for x in status_texts if x).upper()

                # Injury/body part.
                injury_text=""
                for key in ["injury","bodyPart","body_part","details","description","type"]:
                    v=item.get(key)
                    if isinstance(v,dict):
                        injury_text=str(
                            v.get("description") or v.get("name") or
                            v.get("displayName") or v.get("type") or ""
                        ).strip()
                    elif v:
                        injury_text=str(v).strip()
                    if injury_text:
                        break

                # Practice participation.
                practice=""
                practice_candidates=[
                    item.get("practiceStatus"), item.get("practice"),
                    item.get("participation"), item.get("practiceParticipation")
                ]
                for pv in practice_candidates:
                    if isinstance(pv,dict):
                        ptxt=str(
                            pv.get("description") or pv.get("name") or
                            pv.get("abbreviation") or pv.get("type") or ""
                        ).strip()
                    else:
                        ptxt=str(pv or "").strip()
                    if ptxt:
                        practice=ptxt
                        break

                # Infer practice from comments if needed.
                if not practice:
                    raw=status_raw
                    if "DID NOT PARTICIPATE" in raw or re.search(r"\bDNP\b",raw):
                        practice="DNP"
                    elif "LIMITED" in raw:
                        practice="Limited"
                    elif "FULL PARTICIPATION" in raw or re.search(r"\bFULL\b",raw):
                        practice="Full"

                # Normalize weekly game designation.
                designation="ACTIVE"
                if "OUT" in status_raw:
                    designation="OUT"
                elif "DOUBTFUL" in status_raw:
                    designation="DOUBTFUL"
                elif "QUESTIONABLE" in status_raw:
                    designation="QUESTIONABLE"
                elif "SUSPEND" in status_raw:
                    designation="SUSPENDED"
                elif "PHYSICALLY UNABLE" in status_raw or re.search(r"\bPUP\b",status_raw):
                    designation="PUP"
                elif "NON-FOOTBALL" in status_raw or re.search(r"\bNFI\b",status_raw):
                    designation="NFI"
                elif "INJURED RESERVE" in status_raw or "RESERVE/INJURED" in status_raw or re.search(r"\bIR\b",status_raw):
                    designation="IR"
                else:
                    # Practice status alone should not falsely label a player OUT.
                    # DNP/Limited become WATCH state while remaining officially active.
                    designation="ACTIVE"

                updated=str(
                    item.get("date")
                    or item.get("lastUpdated")
                    or item.get("updated")
                    or item.get("updateDate")
                    or ""
                ).strip()

                key=_owner_key(name)
                rec={
                    "status":designation,
                    "injury":injury_text,
                    "practice":practice,
                    "updated":updated,
                    "team":abbr,
                    "source":"Fantasy Edge Injury Watch",
                    "player":name,
                    "practice_source":"ESPN injury report" if practice else ""
                }

                # Prefer the record with a stronger game designation / richer detail.
                priority={"IR":8,"PUP":8,"NFI":8,"SUSPENDED":8,"OUT":7,"DOUBTFUL":6,"QUESTIONABLE":5,"ACTIVE":1}
                prev=out.get(key)
                prev_score=priority.get(str((prev or {}).get("status","ACTIVE")),1) if prev else -1
                new_score=priority.get(designation,1)
                richness=sum(bool(rec.get(k)) for k in ["injury","practice","updated"])
                prev_rich=sum(bool((prev or {}).get(k)) for k in ["injury","practice","updated"]) if prev else -1
                if prev is None or new_score>prev_score or (new_score==prev_score and richness>prev_rich):
                    out[key]=rec

    except Exception as e:
        pass  # cached loaders must not mutate session_state
    return out


@st.cache_data(ttl=900, show_spinner=False)
def _v723_nflverse_practice_feed(season=None):
    """
    Official weekly NFL injury/practice report feed from nflverse.
    Uses practice_status, report_status, injury, team, week, and date_modified.
    """
    out={}
    try:
        if season is None:
            season=int(datetime.now().year)
        url=f"https://github.com/nflverse/nflverse-data/releases/download/injuries/injuries_{int(season)}.csv"
        rr=requests.get(url,timeout=12,headers={"User-Agent":"FantasyEdge/7.23"})
        if rr.status_code!=200 or not rr.content:
            return out
        df=pd.read_csv(io.BytesIO(rr.content),low_memory=False)
        if df.empty:
            return out
        df["_week"]=pd.to_numeric(df.get("week",-1),errors="coerce").fillna(-1)
        if "date_modified" in df.columns:
            df["_modified"]=pd.to_datetime(df["date_modified"],errors="coerce",utc=True)
        else:
            df["_modified"]=pd.NaT
        name_col=next((c for c in ["full_name","player_name","name"] if c in df.columns),None)
        if not name_col:
            return out
        df=df[df[name_col].fillna("").astype(str).str.strip().ne("")].copy()
        df=df.sort_values(["_week","_modified"],ascending=[True,True],na_position="first")

        def _practice(v):
            x=str(v or "").upper().strip()
            if not x or x in ("NAN","NONE"):
                return ""
            if "DID NOT PARTICIPATE" in x or x=="DNP" or "NOT PARTICIPATE" in x:
                return "DNP"
            if "LIMIT" in x:
                return "Limited"
            if "FULL" in x:
                return "Full"
            return str(v).strip()

        def _designation(v):
            x=str(v or "").upper().strip()
            if not x or x in ("NAN","NONE"):
                return "ACTIVE"
            if "OUT" in x: return "OUT"
            if "DOUBTFUL" in x: return "DOUBTFUL"
            if "QUESTIONABLE" in x: return "QUESTIONABLE"
            if x=="IR" or "INJURED RESERVE" in x: return "IR"
            if "PUP" in x: return "PUP"
            if "NFI" in x: return "NFI"
            if "SUSP" in x: return "SUSPENDED"
            return "ACTIVE"

        # Preserve the current report plus same-week practice history.  This lets
        # V7.25 estimate a transparent provisional ramp while today's
        # participation is still pending, without inventing a Full/Limited/DNP.
        histories={}
        for _,r in df.iterrows():
            name=str(r.get(name_col,"") or "").strip()
            key=_owner_key(name)
            if not key:
                continue
            practice=_practice(r.get("practice_status",""))
            report=_designation(r.get("report_status",""))
            injury=str(r.get("practice_primary_injury","") or r.get("report_primary_injury","") or "").strip()
            team=str(r.get("team","") or "").upper().strip()
            modified=r.get("date_modified","")
            modified="" if pd.isna(modified) else str(modified)
            week=int(r.get("_week",-1)) if pd.notna(r.get("_week",-1)) else -1
            rec={"status":report,"injury":injury,"practice":practice,"updated":modified,"team":team,
                 "week":week,"source":"nflverse official injury report",
                 "player":name,
                 "practice_source":"nflverse official injury report" if practice else ""}
            histories.setdefault(key,[]).append({"week":week,"practice":practice,"updated":modified,"status":report,"injury":injury})
            prev=out.get(key)
            if prev is None:
                out[key]=rec
            else:
                pw=int(prev.get("week",-1) or -1); nw=int(rec.get("week",-1) or -1)
                # Newer week always wins.  Within a week, newer rows win even if
                # participation is blank, because that blank may represent a
                # newly matched report whose practice field has not published yet.
                prev_dt=pd.to_datetime(prev.get("updated",""),errors="coerce",utc=True)
                rec_dt=pd.to_datetime(rec.get("updated",""),errors="coerce",utc=True)
                newer=(pd.notna(rec_dt) and (pd.isna(prev_dt) or rec_dt>=prev_dt))
                if nw>pw or (nw==pw and newer):
                    out[key]=rec

        for key,rec in list(out.items()):
            week=int(rec.get("week",-1) or -1)
            hist=[h for h in histories.get(key,[]) if int(h.get("week",-1) or -1)==week]
            hist=sorted(hist,key=lambda h: pd.to_datetime(h.get("updated",""),errors="coerce",utc=True) if h.get("updated") else pd.Timestamp.min.tz_localize("UTC"))
            published=[h for h in hist if str(h.get("practice","") or "").strip()]
            prior=published[-1] if published else None
            prior2=published[-2] if len(published)>=2 else None
            rec["prior_practice"] = str(prior.get("practice","") if prior else "")
            rec["prior_practice_updated"] = str(prior.get("updated","") if prior else "")
            if prior and prior2:
                rec["practice_trend"] = f"{prior2.get('practice','')} → {prior.get('practice','')}"
            elif prior:
                rec["practice_trend"] = str(prior.get("practice","") or "")
            else:
                rec["practice_trend"] = ""
        return out
    except Exception:
        return out


@st.cache_data(ttl=900, show_spinner=False)
def _v680_injury_watch_feed():
    """
    Unified Injury Watch:
    1) Sleeper injury-specific fields (most reliable for weekly fantasy tags)
    2) ESPN injury report enrichment when available
    """
    sleeper=_v681_sleeper_injury_watch()
    espn=_v680_espn_injury_watch_feed()
    official=_v723_nflverse_practice_feed()

    merged={k:dict(v) for k,v in (sleeper or {}).items()}
    priority={"IR":8,"PUP":8,"NFI":8,"SUSPENDED":8,"OUT":7,"DOUBTFUL":6,"QUESTIONABLE":5,"ACTIVE":1}

    for key,rec in (espn or {}).items():
        if not isinstance(rec,dict):
            continue
        if key not in merged:
            merged[key]=dict(rec)
            continue

        base=merged[key]
        bs=_v677_normalize_injury_status(base.get("status","ACTIVE"))
        es=_v677_normalize_injury_status(rec.get("status","ACTIVE"))

        # Stronger designation wins.
        if priority.get(es,1)>priority.get(bs,1):
            base["status"]=es
            base["source"]=rec.get("source",base.get("source",""))

        # ESPN may enrich missing detail even when Sleeper carries the designation.
        for fld in ["practice","injury","updated","team","player"]:
            if not str(base.get(fld,"") or "").strip() and str(rec.get(fld,"") or "").strip():
                base[fld]=rec.get(fld)
        if str(rec.get("practice","") or "").strip() and not str(base.get("practice_source","") or "").strip():
            base["practice_source"]=rec.get("practice_source") or rec.get("source","")

        merged[key]=base

    # V7.23: official weekly NFL injury reports are the practice-participation
    # authority. They enrich Full/Limited/DNP while preserving stronger reserve
    # and game designations already supplied by Sleeper/ESPN.
    for key,rec in (official or {}).items():
        if not isinstance(rec,dict):
            continue
        if key not in merged:
            merged[key]=dict(rec)
            continue
        base=merged[key]
        bs=_v677_normalize_injury_status(base.get("status","ACTIVE"))
        os=_v677_normalize_injury_status(rec.get("status","ACTIVE"))
        if priority.get(os,1)>priority.get(bs,1):
            base["status"]=os
        if str(rec.get("practice","") or "").strip():
            base["practice"]=rec.get("practice")
            base["practice_source"]=rec.get("practice_source") or rec.get("source","")
        if str(rec.get("player","") or "").strip() and not str(base.get("player","") or "").strip():
            base["player"]=rec.get("player")
        if str(rec.get("injury","") or "").strip():
            base["injury"]=rec.get("injury")
        if str(rec.get("updated","") or "").strip():
            base["updated"]=rec.get("updated")
        for fld in ["prior_practice","prior_practice_updated","practice_trend"]:
            if str(rec.get(fld,"") or "").strip():
                base[fld]=rec.get(fld)
        if str(rec.get("team","") or "").strip() and not str(base.get("team","") or "").strip():
            base["team"]=rec.get("team")
        base["source"]=" + ".join(dict.fromkeys([x for x in [str(base.get("source","") or ""),str(rec.get("source","") or "")] if x]))
        merged[key]=base

    return merged


def _v724_name_parts(name):
    raw=str(name or "").strip()
    toks=[re.sub(r"[^A-Za-z0-9'-]","",x) for x in raw.split()]
    toks=[x for x in toks if x]
    if toks and toks[-1].lower().rstrip('.') in {"jr","sr","ii","iii","iv","v"}:
        toks=toks[:-1]
    first=toks[0].lower() if toks else ""
    last=toks[-1].lower() if toks else ""
    return first,last


def _v724_resolve_watch_record(name,team,watch):
    """Resolve an injury/practice record without unsafe fuzzy player matching.

    Order: canonical identity -> exact normalized display name -> unique team+last
    name -> unique team+first-initial+last.  Team-aware fallbacks are deliberately
    conservative so similarly named NFL players cannot be cross-wired.
    Returns (record, match_method).
    """
    if not isinstance(watch,dict):
        return {},"none"
    key=_owner_key(name)
    rec=watch.get(key)
    if isinstance(rec,dict):
        return rec,"canonical"

    target_team=str(team or "").upper().strip()
    tf,tl=_v724_name_parts(name)
    candidates=[]
    seen=set()
    for _,r in watch.items():
        if not isinstance(r,dict):
            continue
        pname=str(r.get("player","") or "").strip()
        if not pname:
            continue
        sig=(str(r.get("player_id","") or ""), _owner_key(pname), str(r.get("team","") or "").upper())
        if sig in seen:
            continue
        seen.add(sig)
        rf,rl=_v724_name_parts(pname)
        rteam=str(r.get("team","") or "").upper().strip()
        # Exact normalized display-name identity, independent of dict key.
        if _owner_key(pname)==key:
            return r,"display-name"
        if target_team and rteam and target_team==rteam and tl and rl==tl:
            candidates.append((r,rf,rl))

    if len(candidates)==1:
        return candidates[0][0],"team+last"
    if candidates and tf:
        init=[r for r,rf,rl in candidates if rf and rf[:1]==tf[:1]]
        if len(init)==1:
            return init[0],"team+initial+last"
    return {},"none"

def _v680_practice_risk(practice):
    s=str(practice or "").upper().strip()
    if not s:
        return ""
    if "DNP" in s or "DID NOT PARTICIPATE" in s:
        return "🔴 DNP"
    if "LIMIT" in s:
        return "🟡 LIMITED"
    if "FULL" in s:
        return "🟢 FULL"
    return s

# ---------------- V6.79 authoritative NFL reserve-list status ----------------
# Sleeper's generic player record can say "Active" for players who are actually
# on Reserve/IR or Reserve/PUP. This feed uses current official roster-list
# designations from ESPN's athlete API as a second live source, and merges them
# conservatively: reserve/unavailable designations override generic ACTIVE.
@st.cache_data(ttl=1800, show_spinner=False)
def _v679_espn_roster_status():
    out={}
    try:
        # Pull all 32 current NFL team rosters from ESPN's public API.
        teams_url="https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams?limit=40"
        tr=requests.get(teams_url,timeout=8,headers={"User-Agent":"Mozilla/5.0"})
        tr.raise_for_status()
        teams=((tr.json().get("sports") or [{}])[0].get("leagues") or [{}])[0].get("teams") or []
        for tw in teams:
            team=(tw.get("team") or {})
            slug=str(team.get("slug") or "").strip()
            abbr=str(team.get("abbreviation") or "").upper().strip()
            if not slug:
                continue
            try:
                url=f"https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams/{slug}/roster"
                rr=requests.get(url,timeout=6,headers={"User-Agent":"Mozilla/5.0"})
                if rr.status_code != 200:
                    continue
                data=rr.json()
                for group in data.get("athletes",[]) or []:
                    group_name=str(group.get("position") or group.get("name") or "").upper()
                    for a in group.get("items",[]) or []:
                        name=str(a.get("fullName") or a.get("displayName") or "").strip()
                        if not name:
                            continue
                        # ESPN commonly exposes status in status.type/name/description;
                        # roster grouping can also carry reserve-list wording.
                        st=a.get("status") or {}
                        vals=[]
                        if isinstance(st,dict):
                            vals += [st.get("name"),st.get("type"),st.get("description"),st.get("abbreviation")]
                        elif st:
                            vals.append(st)
                        vals += [a.get("status"),group_name]
                        raw=" | ".join(str(x) for x in vals if x).upper()

                        designation="ACTIVE"
                        if "PHYSICALLY UNABLE" in raw or re.search(r"\bPUP\b",raw):
                            designation="PUP"
                        elif "NON-FOOTBALL" in raw or re.search(r"\bNFI\b",raw):
                            designation="NFI"
                        elif "SUSPEND" in raw:
                            designation="SUSPENDED"
                        elif "INJURED RESERVE" in raw or "RESERVE/INJURED" in raw or re.search(r"\bIR\b",raw):
                            designation="IR"
                        elif "OUT" in raw:
                            designation="OUT"
                        elif "DOUBTFUL" in raw:
                            designation="DOUBTFUL"
                        elif "QUESTIONABLE" in raw:
                            designation="QUESTIONABLE"

                        out[_owner_key(name)]={
                            "status":designation,
                            "team":abbr,
                            "source":"ESPN roster designation"
                        }
            except Exception:
                continue
    except Exception as e:
        pass  # cached loaders must not mutate session_state
    return out

# Current official reserve-list corrections verified from team transaction/roster
# publications. These are a safety net for reserve designations that generic APIs
# may flatten to Active. Keep this small and only for verified reserve placements.
_V679_VERIFIED_RESERVE = {
    _owner_key("Tank Dell"): {"status":"IR","source":"Official team reserve list","earliest_week":5},
    _owner_key("Brian Branch"): {"status":"PUP","source":"Official team reserve list"},
    _owner_key("Kerby Joseph"): {"status":"PUP","source":"Official team reserve list"},
}

def _v679_authoritative_status(name, generic_status, roster_status=None, injury_watch=None):
    generic=_v677_normalize_injury_status(generic_status)
    key=_owner_key(name)

    # Verified reserve placements have highest automated priority.
    fixed=_V679_VERIFIED_RESERVE.get(key)
    if fixed:
        return fixed["status"],fixed["source"]

    # Current roster reserve designation outranks weekly injury report.
    live=(roster_status or {}).get(key)
    if isinstance(live,dict):
        live_status=_v677_normalize_injury_status(live.get("status","ACTIVE"))
        if live_status in ("IR","PUP","NFI","SUSPENDED"):
            return live_status,live.get("source","ESPN roster designation")

    # Fantasy Edge Injury Watch supplies current game designation.
    watch=(injury_watch or {}).get(key)
    if isinstance(watch,dict):
        watch_status=_v677_normalize_injury_status(watch.get("status","ACTIVE"))
        if watch_status in ("OUT","DOUBTFUL","QUESTIONABLE","IR","PUP","NFI","SUSPENDED"):
            return watch_status,watch.get("source","Fantasy Edge Injury Watch")

    # Preserve a meaningful generic/live injury status if Injury Watch has no stronger record.
    if generic in ("OUT","DOUBTFUL","QUESTIONABLE","IR","PUP","NFI","SUSPENDED"):
        return generic,"Sleeper / injury feed"

    return generic,"Sleeper / injury feed"

# --- Fantasy Edge v9.2 live injury overlay ---
def _injury_overlay_penalty(status):
    x=_v677_normalize_injury_status(status).strip().lower()
    if x in ["do not draft","dnr","avoid"]: return 999.0
    if x in ["ir","reserve/ir","nfi","reserve/nfi"]: return 999.0
    if x in ["pup","reserve/pup"]: return 3.5
    if x in ["out","o","suspended","susp"]: return 2.5
    if x in ["doubtful","d"]: return 1.25
    if x in ["questionable","q"]: return 0.9
    return 0.0

def _injury_overlay_severity(status):
    p=_injury_overlay_penalty(status)
    if p>=900: return 3
    if p>=2.5: return 2
    if p>0: return 1
    return 0

def apply_v92_injury_overlay(board,state):
    """Overlay Sleeper injury status with user-controlled manual overrides."""
    b=board.copy()
    overrides=state.get("injury_overrides",{}) or {}
    b["injury_auto"]=b.get("injury",pd.Series("",index=b.index)).fillna("").astype(str)
    effective=[]
    source=[]
    for _,r in b.iterrows():
        ov=overrides.get(norm(r["player"]))
        if ov and str(ov).upper()!="AUTO":
            effective.append("" if str(ov).upper()=="CLEAR" else str(ov))
            source.append("Manual")
        else:
            effective.append(str(r["injury_auto"] or ""))
            source.append("Sleeper")
    b["injury_effective"]=[_v677_normalize_injury_status(x) for x in effective]
    b["injury_source"]=source

    # V6.79 authority merge. Manual override remains king; otherwise reserve-list
    # status can override a stale/generic ACTIVE designation.
    _eff=[]
    _src=[]
    _body=[]
    _practice=[]
    _updated=[]
    _practice_source=[]
    _practice_match=[]
    _prior_practice=[]
    _practice_trend=[]
    _prior_practice_updated=[]
    _v679_live_status=_v679_espn_roster_status()
    _v680_watch=_v680_injury_watch_feed()

    for i,row in b.iterrows():
        current=_v677_normalize_injury_status(row.get("injury_effective","ACTIVE"))
        current_source=str(row.get("injury_source","") or "")
        key=_owner_key(row.get("player",""))
        watch,watch_match=_v724_resolve_watch_record(
            row.get("player",""),row.get("team",""),_v680_watch
        )

        if current_source.lower().startswith("manual"):
            final,final_source=current,current_source
        else:
            final,final_source=_v679_authoritative_status(
                row.get("player",""),current,_v679_live_status,_v680_watch
            )
            if final==current and final_source=="Sleeper / injury feed":
                final_source=current_source or final_source

        _eff.append(final)
        _src.append(final_source)
        _body.append(str(watch.get("injury","") or ""))
        _practice.append(str(watch.get("practice","") or ""))
        _updated.append(str(watch.get("updated","") or ""))
        _practice_source.append(str(watch.get("practice_source","") or (watch.get("source","") if watch.get("practice") else "")))
        _prior_practice.append(str(watch.get("prior_practice","") or ""))
        _practice_trend.append(str(watch.get("practice_trend","") or ""))
        _prior_practice_updated.append(str(watch.get("prior_practice_updated","") or ""))
        if watch_match!="none":
            _practice_match.append("practice found" if str(watch.get("practice","") or "").strip() else "report matched; participation not published")
        else:
            _practice_match.append("no practice report matched")

    b["injury_effective"]=_eff
    b["injury_source"]=_src
    b["injury_detail"]=_body
    b["practice_status"]=_practice
    b["injury_updated"]=_updated
    b["practice_source"]=_practice_source
    b["practice_match_status"]=_practice_match
    b["prior_practice_status"]=_prior_practice
    b["practice_trend"]=_practice_trend
    b["prior_practice_updated"]=_prior_practice_updated
    b["practice_display"]=b["practice_status"].map(_v680_practice_risk)
    b["injury"]=b["injury_effective"]
    b["injury_designation"]=b["injury_effective"].map(_v677_status_icon)
    b["injury_penalty"]=b["injury_effective"].map(_injury_overlay_penalty).astype(float)
    b["injury_severity"]=b["injury_effective"].map(_injury_overlay_severity).astype(int)
    return b


# --- Fantasy Edge v9.24 dynamic roster opportunity cost ---

def _v934_num(row, *keys):
    for k in keys:
        if k in row.index:
            v = pd.to_numeric(pd.Series([row.get(k, np.nan)]), errors="coerce").iloc[0]
            if pd.notna(v):
                return float(v)
    return np.nan

_V937_IDP_DB_CONSENSUS = {'Brian Branch': 1, 'Nick Emmanwori': 2, 'Kyle Hamilton': 3, 'Derwin James': 4, 'Nick Cross': 5, 'Jessie Bates': 6, 'Antoine Winfield Jr.': 7, 'Tykee Smith': 8, 'Cooper DeJean': 9, 'Devon Witherspoon': 10, 'DeShon Elliott': 11, 'Xavier McKinney': 12, 'Budda Baker': 13, 'Julian Love': 14, 'Christian Gonzalez': 20, 'Sauce Gardner': 25, 'Pat Surtain II': 30, 'Denzel Ward': 35}

_V936_IDP_DL_CONSENSUS = {
    "Myles Garrett": 1,
    "Maxx Crosby": 3,
    "Aidan Hutchinson": 4,
    "Brian Burns": 5,
    "Will Anderson Jr.": 6,
    "Danielle Hunter": 7,
    "T.J. Watt": 9,
    "Nick Bosa": 12,
    "Trey Hendrickson": 13,
    "Micah Parsons": 15,
    "Jeffery Simmons": 16,
    "Andrew Van Ginkel": 8,
    "Nik Bonitto": 10,
    "Tuli Tuipulotu": 11,
}

def _v936_external_idp_rank(row):
    name=str(row.get("player", row.get("Player",""))).strip()
    pos=str(row.get("position", row.get("Position",""))).upper()
    if pos=="DB":
        return _V937_IDP_DB_CONSENSUS.get(name, np.nan)
    if pos=="DL":
        return _V936_IDP_DL_CONSENSUS.get(name, np.nan)
    return np.nan


@st.cache_data(show_spinner=False)
def _v938_unified_player_universe(board):
    """Canonical Draft/Mock lobby universe with complete IDP market proxies."""
    if board is None or len(board)==0:
        return board
    x=board.copy()
    if "key" not in x.columns:
        x["key"]=x["player"].astype(str).map(norm)

    overlays=[]
    for name,rank in _V936_IDP_DL_CONSENSUS.items():
        overlays.append((name,"DL",int(rank)))
    for name,rank in _V937_IDP_DB_CONSENSUS.items():
        overlays.append((name,"DB",int(rank)))

    def _proxy(pos,rank):
        if pos=="DL":
            market=float(np.clip(100.0+4.0*rank,101.0,184.0))
            proj=float(max(4.8,10.0-0.28*(rank-1)))
            repl=6.2
        else:
            market=float(np.clip(108.0+3.6*rank,110.0,186.0))
            proj=float(max(4.8,9.2-0.20*(rank-1)))
            repl=5.9
        vorp=float(proj-repl)
        model_rank=float(market-max(0.0,min(18.0,vorp*3.0)))
        base=float(7.0+max(0.0,22.0-rank)*0.55+max(vorp,0)*1.5)
        strength=float(max(52.0,88.0-rank*1.25))
        return market,proj,vorp,model_rank,base,strength

    rows=[]
    existing_keys=set(x["key"].astype(str))
    for name,pos,rank in overlays:
        key=norm(name)
        market,proj,vorp,model_rank,base,strength=_proxy(pos,rank)

        if key in existing_keys:
            mask=x["key"].astype(str).eq(key)
            updates={
                "position":pos,"raw_position":pos,
                "market_pick":market,"consensus_rank":market,
                "model_rank":model_rank,"projection":proj,"vorp":vorp,
                "consensus_strength":strength,"pure_model_score":base,
                "draft_score":base,"confidence":0.78,
                "v9_market_pick":market,"v9_vorp":vorp,
                "v9_draft_score":base,"v9_model_rank":model_rank,
                "v9_base_live_score":base,
            }
            for col,val in updates.items():
                if col in x.columns:
                    x.loc[mask,col]=val
            continue

        d={c:np.nan for c in x.columns}
        d.update({
            "id":"v948:"+key,"player":name,"key":key,
            "position":pos,"raw_position":pos,"team":"NFL",
            "age":np.nan,"exp":np.nan,"injury":"",
            "last_ppg":proj,"prior_ppg":proj,"opp_pg":proj,
            "td_rate_z":0.0,"eff_z":0.0,"growth_z":0.0,"opp_z":0.0,
            "idp_vol_z":0.0,"bigplay_z":0.0,
            "projection":proj,"vorp":vorp,"replacement_ppg":proj-vorp,
            "progression":0.0,"regression":0.0,"scarcity":0.0,
            "consensus_strength":strength,"consensus_rank":market,
            "market_pick":market,"model_rank":model_rank,
            "pure_model_score":base,"draft_score":base,"confidence":0.78,
            "identity_key":"v948:"+key+"|"+pos,
            "v9_market_pick":market,"v9_vorp":vorp,
            "v9_draft_score":base,"v9_model_rank":model_rank,
            "v9_base_live_score":base,
        })
        rows.append(d)

    if rows:
        x=pd.concat([x,pd.DataFrame(rows)],ignore_index=True,sort=False)
    return x.drop_duplicates(subset=["key"],keep="first").reset_index(drop=True)


def _v941_idp_quality(row):
    """Independent positional-quality support; never sufficient alone for eligibility."""
    pos=str(row.get("position","")).upper()
    ext=_v936_external_idp_rank(row)
    proj=_v934_num(row,"projection","proj","fantasy_points","projected_points")
    vorp=_v934_num(row,"vorp","v9_vorp","VORP")
    market=_v934_num(row,"market_pick","adp","consensus_pick","consensus_rank")
    evidence=0
    if pd.notna(proj) and proj>0: evidence+=1
    if pd.notna(vorp) and vorp>0: evidence+=1
    if pd.notna(market): evidence+=1
    # tier is support, not authority
    if pd.notna(ext):
        if pos=="DL":
            tier = 1 if ext<=6 else 2 if ext<=15 else 3 if ext<=30 else 4
        else:
            tier = 1 if ext<=8 else 2 if ext<=20 else 3 if ext<=40 else 4
    else:
        tier=5
    return tier,evidence

def _v935_idp_impact_score(row):
    """IDP impact with independent-evidence gating; duplicated fallback rank/market
    cannot manufacture confidence. No hard-coded player names."""
    pos = str(row.get("position","")).upper()
    if pos not in ("DL","DB"):
        return np.nan, False, 0

    vorp = _v934_num(row, "vorp", "VORP")
    proj = _v934_num(row, "projection", "proj", "fantasy_points", "points")
    market = _v934_num(row, "market_pick", "adp", "consensus_pick")
    rank = _v934_num(row, "consensus_rank", "rank", "model_rank")
    ext_rank = _v936_external_idp_rank(row)
    snaps = _v934_num(row, "snap_share", "snaps_pct", "snap_pct")
    tackles = _v934_num(row, "tackles", "total_tackles", "combined_tackles")
    sacks = _v934_num(row, "sacks")
    tfl = _v934_num(row, "tfl", "tackles_for_loss")
    pressures = _v934_num(row, "pressures", "qb_pressures")
    ints = _v934_num(row, "interceptions", "ints")
    ff = _v934_num(row, "forced_fumbles", "ff")
    pdff = _v934_num(row, "passes_defended", "pass_deflections", "pd")

    # Independent evidence = meaningful player-specific signal, not mere presence.
    # Zero VORP is neutral/missing support, not positive evidence.
    independent = 0
    production = [tackles, sacks, tfl, pressures, ints, ff, pdff]
    if pd.notna(vorp) and abs(vorp) > 1e-9: independent += 1
    if pd.notna(proj) and proj > 0: independent += 1
    if pd.notna(snaps) and snaps > 0: independent += 1
    if any(pd.notna(v) and v > 0 for v in production): independent += 1
    if pd.notna(ext_rank):
        independent += 1

    # Market/rank can support ordering, but only one combined market-family signal
    # and it cannot make an otherwise unsupported IDP eligible.
    market_support = int(
        (pd.notna(market) and market > 0) or
        (pd.notna(rank) and rank > 0)
    )

    score = 0.0
    if pd.notna(vorp) and abs(vorp) > 1e-9:
        score += 7.0 * max(vorp, -1.0)
    if pd.notna(proj) and proj > 0:
        score += min(proj, 250.0) * 0.035
    if pd.notna(snaps) and snaps > 0:
        score += max(0.0, snaps) * (0.06 if snaps <= 1.5 else 0.0008)
    for val, wt in [(tackles,.08),(sacks,1.1),(tfl,.45),(pressures,.12),
                    (ints,1.25),(ff,1.1),(pdff,.22)]:
        if pd.notna(val) and val > 0:
            score += val * wt
    if pd.notna(ext_rank):
        if pos=="DB":
            score += max(0.0, 40.0 - float(ext_rank)) * 0.55
        else:
            score += max(0.0, 18.0 - float(ext_rank)) * 1.15
    if pos=="DL":
        if pd.notna(sacks) and sacks>0: score += sacks*.35
        if pd.notna(pressures) and pressures>0: score += pressures*.05
    else:
        if pd.notna(tackles) and tackles>0: score += tackles*.03
        if pd.notna(ints) and ints>0: score += ints*.30

    # Market is deliberately only a modest tie-breaker after independent support.
    if independent:
        if pd.notna(market) and market > 0:
            score += max(0.0, 180.0-market) * 0.010
        if pd.notna(rank) and rank > 0:
            score += max(0.0, 250.0-rank) * 0.006

    strong_single = (
        (pd.notna(vorp) and vorp >= 1.0) or
        (pd.notna(proj) and proj > 0) or
        any(pd.notna(v) and v > 0 for v in production)
    )
    # v9.40: external prior is only a tie-breaker/support signal.
    # It can never, by itself, make an IDP eligible.
    eligible = independent >= 2 or strong_single
    evidence = independent + market_support
    return float(score), bool(eligible), int(evidence)

# Backward-compatible name used by the rest of the app.
def _v934_idp_impact_score(row):
    return _v935_idp_impact_score(row)

def roster_opportunity_adjustment(df, roster, round_no, current_pick, slots):
    """
    Temporary roster-construction overlay.
    Negative values = opportunity-cost penalty.
    Positive values = roster-need bonus.
    The frozen player board is not modified.
    """
    x=df.copy()
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    rnd=int(round_no)
    cur=int(current_pick)

    adjustments=[]
    reasons=[]
    for _,r in x.iterrows():
        pos=str(r.get("position",""))
        adj=0.0
        why=[]

        rb=counts.get("RB",0)
        wr=counts.get("WR",0)
        qb=counts.get("QB",0)
        te=counts.get("TE",0)
        dl=counts.get("DL",0)
        db=counts.get("DB",0)

        # WR foundation pressure: avoid entering the middle/late draft too thin at WR.
        if pos=="WR":
            if rnd<=8 and wr<2:
                adj += 6.0
                why.append("WR foundation need")
            elif rnd<=9 and wr<3:
                adj += 4.0
                why.append("WR depth need")
            elif rnd<=11 and wr<4:
                adj += 2.0
                why.append("WR depth")

        # RB saturation: increasingly expensive once the roster is already deep.
        if pos=="RB":
            if rb>=5:
                adj -= 10.0
                why.append("RB6+ saturation")
            elif rb>=4:
                adj -= 6.0
                why.append("RB5 opportunity cost")
            elif rb>=3 and rnd<=9 and wr<3:
                adj -= 3.5
                why.append("RB4 vs WR need")

        # v9.26 QB2 opportunity-cost correction for standard 1-QB builds.
        if pos=="QB" and qb>=1:
            qb_rows=roster[roster.position.eq("QB")] if roster is not None and len(roster) else pd.DataFrame()
            early_qb1=False
            elite_qb1=False
            if len(qb_rows):
                if "mock_round" in qb_rows.columns:
                    early_qb1=pd.to_numeric(qb_rows["mock_round"],errors="coerce").min() <= 6
                elif "draft_round" in qb_rows.columns:
                    early_qb1=pd.to_numeric(qb_rows["draft_round"],errors="coerce").min() <= 6
                if "model_rank" in qb_rows.columns:
                    elite_qb1=pd.to_numeric(qb_rows["model_rank"],errors="coerce").min() <= 36
                if "vorp" in qb_rows.columns:
                    elite_qb1=elite_qb1 or (pd.to_numeric(qb_rows["vorp"],errors="coerce").max() >= 35)

            if early_qb1 or elite_qb1:
                if rnd<=12:
                    adj -= 18.0
                    why.append("QB2 blocked by early/elite QB1")
                elif rnd<=14:
                    adj -= 10.0
                    why.append("QB2 high opportunity cost")
                else:
                    adj -= 5.0
                    why.append("late QB2 after strong QB1")
            else:
                if rnd<=10:
                    adj -= 12.0
                    why.append("QB2 after QB1")
                elif rnd<=13:
                    adj -= 10.0
                    why.append("QB2 opportunity cost")
                else:
                    adj -= 7.0
                    why.append("late QB2 must beat bench alternatives")

        # v9.29 WR foundation + RB saturation correction.
        # Prevent RB4+ accumulation from crowding out a thin WR room.
        if pos=="WR":
            if rnd>=7 and wr<4:
                adj += 12.0
                why.append("WR foundation priority")
            if rnd>=10 and wr<5:
                adj += 9.0
                why.append("WR bench-depth priority")

        if pos=="RB":
            if rb>=4 and wr<4:
                adj -= 18.0
                why.append("RB saturation vs thin WR")
            elif rb>=5 and wr<5:
                adj -= 14.0
                why.append("RB saturation vs WR depth")
            elif rb>=6:
                adj -= 20.0
                why.append("extreme RB saturation")

        # v9.44 required TE1 construction.
        # TE remains value-sensitive early, but cannot be left unfilled late.
        if pos=="TE" and te<1:
            if rnd>=13:
                adj += 16.0
                why.append("required TE still open")
            elif rnd>=9:
                adj += 8.0
                why.append("TE1 roster need")
            elif rnd>=6:
                adj += 3.0
                why.append("TE1 value window")

        # v9.30 onesie-value gate.
        # QB2/TE2 must clear actual model-value evidence; being far past ADP alone is insufficient.
        _v930_vorp = pd.to_numeric(pd.Series([r.get("vorp", np.nan)]), errors="coerce").iloc[0]
        _v930_cons = pd.to_numeric(pd.Series([r.get("consensus_rank", r.get("rank", np.nan))]), errors="coerce").iloc[0]

        if pos=="QB" and qb>=1:
            if pd.isna(_v930_vorp) or _v930_vorp < 2.0:
                adj -= 22.0
                why.append("QB2 fails exceptional-value gate")
            elif rnd<=12:
                adj -= 8.0
                why.append("QB2 exceptional value but early")

        if pos=="TE" and te>=1:
            if pd.isna(_v930_vorp) or _v930_vorp < 2.0:
                adj -= 18.0
                why.append("TE2 fails exceptional-value gate")
            elif rnd<=11:
                adj -= 7.0
                why.append("TE2 exceptional value but early")

        # v9.27.1 coordinated TE2 opportunity cost.
        # Preserve the existing v9.26 QB2 logic unchanged. TE2 now competes
        # more directly with unfinished WR/RB bench depth, but remains a soft penalty.
        offense_depth_thin = (wr < (4 if rnd<=12 else 5)) or (rb < (4 if rnd<=11 else 5))
        if pos=="TE" and te>=1:
            if rnd<=10 and offense_depth_thin:
                adj -= 18.0
                why.append("TE2 vs unfinished WR/RB depth")
            elif rnd<=12 and offense_depth_thin:
                adj -= 11.0
                why.append("TE2 opportunity cost vs depth")
            else:
                adj -= 7.0
                why.append("TE2 must beat bench alternatives")

        # Delay IDP if core offense is still materially incomplete.
        core_offense_incomplete = (wr<4) or (qb<1) or (te<1)
        if pos in ["DL","DB"] and rnd<=12 and core_offense_incomplete:
            if pos=="DB":
                adj -= 9.0
                why.append("DB vs unfinished offense")
            else:
                adj -= 7.0
                why.append("DL vs unfinished offense")

        # v9.34 dedicated IDP impact mechanism.
        if pos in ["DL","DB"]:
            _idp_score, _idp_eligible, _idp_evidence = _v934_idp_impact_score(r)
            _idp_vorp = _v934_num(r, "vorp", "VORP")
            if not _idp_eligible:
                adj -= 75.0
                why.append("IDP insufficient evidence")
            else:
                adj += min(max(_idp_score, -10.0), 20.0)
                why.append(f"IDP impact {_idp_score:.1f}")
            if pd.notna(_idp_vorp) and _idp_vorp <= 0 and _idp_score < 8.0:
                adj -= 30.0
                why.append("IDP zero-VORP without impact support")
            _idp_market = _v934_num(r, "market_pick", "adp", "consensus_pick")
            _idp_rank = _v934_num(r, "consensus_rank", "rank", "model_rank")
            if pos=="DB" and pd.isna(_idp_market) and pd.isna(_idp_rank):
                adj -= 28.0
                why.append("DB lacks independent market support")

        # Harder pressure against early DB specifically; DB is usually replaceable.
        if pos=="DB" and rnd<=10:
            adj -= 4.0
            why.append("early DB cost")

        # V6.11 consolidated IDP depth economics. Required DL/DB starters still
        # receive normal discipline, but a Tier 1-2 IDP3 is not triple-taxed by
        # starter-filled + depth + exact-construction penalties.
        _tier_depth=pd.to_numeric(pd.Series([r.get("idp_quality_tier",np.nan)]),errors="coerce").iloc[0]
        _impact_depth=pd.to_numeric(pd.Series([r.get("idp_impact_score",np.nan)]),errors="coerce").iloc[0]
        _elite_depth=(pd.notna(_tier_depth) and _tier_depth<=2) or (pd.notna(_impact_depth) and _impact_depth>=8.0)
        _idp_count_now=dl+db
        if pos=="DL" and dl>=1:
            adj -= 4.0 if (_idp_count_now>=2 and _elite_depth and rnd>=11) else 22.0
            why.append("elite DL3 bench competition" if (_idp_count_now>=2 and _elite_depth and rnd>=11) else "DL starter already filled")
        if pos=="DB" and db>=1:
            adj -= 4.0 if (_idp_count_now>=2 and _elite_depth and rnd>=11) else 22.0
            why.append("elite DB3 bench competition" if (_idp_count_now>=2 and _elite_depth and rnd>=11) else "DB starter already filled")

        # v9.27.1 conditional IDP2 opportunity cost.
        # A second defender is optional depth, not a required roster target.
        # If offensive depth is still thin, discourage IDP2. Once offense is healthy
        # and the draft is late, allow a strong second defender to win naturally.
        idp_count=dl+db
        if pos in ["DL","DB"] and idp_count>=2:
            # A third defender is a value-responsive bench option only.
            _tier=pd.to_numeric(pd.Series([r.get("idp_quality_tier",np.nan)]),errors="coerce").iloc[0]
            _impact=pd.to_numeric(pd.Series([r.get("idp_impact_score",np.nan)]),errors="coerce").iloc[0]
            _elite_extra=(pd.notna(_tier) and _tier<=2) or (pd.notna(_impact) and _impact>=8.0)
            if offense_depth_thin:
                adj -= 4.0 if _elite_extra and rnd>=11 else 14.0
                why.append("elite IDP3 vs depth competition" if _elite_extra and rnd>=11 else "IDP3 vs offensive depth")
            elif rnd<=12:
                adj -= 10.0
                why.append("IDP3 too early")
            elif _elite_extra:
                adj += 2.5
                why.append("elite late IDP3 value")
            else:
                adj -= 8.0
                why.append("non-impact IDP3")
        elif pos in ["DL","DB"] and idp_count>=1:
            if offense_depth_thin:
                adj -= 8.0
                why.append("IDP2 vs offensive depth")
            elif rnd<=11:
                adj -= 4.0
                why.append("early IDP2 opportunity cost")
            else:
                adj += 0.5
                why.append("late IDP2 neutral")

        # Guarantee starter needs near the end.
        picks_left=max(0, int(slots.get("QB",0)+slots.get("RB",0)+slots.get("WR",0)+slots.get("TE",0)+
                              slots.get("DL",0)+slots.get("DB",0)+slots.get("FLEX",0)+slots.get("K",0)) - len(roster))
        missing_required=0
        for p in ["QB","RB","WR","TE","DL","DB"]:
            missing_required += max(int(slots.get(p,0))-int(counts.get(p,0)),0)
        if picks_left<=missing_required+1:
            if counts.get(pos,0) < int(slots.get(pos,0)):
                adj += 10.0
                why.append("required starter urgency")

        # Extreme-faller relief: preserve the ability to take truly unusual value.
        mp=pd.to_numeric(pd.Series([r.get("market_pick",np.nan)]),errors="coerce").iloc[0]
        if pd.notna(mp):
            fall=max(cur-float(mp),0.0)
            if fall>=24 and adj<0:
                adj *= 0.35
                why.append("extreme-faller relief")
            elif fall>=16 and adj<0:
                adj *= 0.60
                why.append("faller relief")

        adjustments.append(float(adj))
        reasons.append("; ".join(why) if why else "balanced")

    x["roster_opportunity_adj"]=adjustments
    x["roster_opportunity_note"]=reasons
    return x


def apply_v932_exact_league_construction(df, roster, round_no, rounds, slots):
    """Exact user league shape: 1 QB, 2 RB, 2 WR, 2 FLEX, 1 K, 1 DL, 1 DB, 6 bench.
    K is reserved for the endgame and ranked with market-derived projection plus position-relative VORP.
    """
    x=df.copy()
    if x.empty or "evaluation_score" not in x.columns:
        return x
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    rnd=int(round_no); total=int(rounds)
    qb,rb,wr,te,dl,db=[int(counts.get(p,0)) for p in ["QB","RB","WR","TE","DL","DB"]]
    flex_eligible=rb+wr+te
    # Two FLEX means six RB/WR/TE starter-quality bodies are required before pure depth.
    for idx,r in x.iterrows():
        pos=str(r.get("position","")); adj=0.0; why=[]
        if pos in ["RB","WR","TE"]:
            if flex_eligible < 6:
                adj += 4.5
                why.append("2-FLEX starter construction")
            if pos=="WR" and wr<2: adj += 4.0
            if pos=="RB" and rb<2: adj += 3.0
        # Strong QB2/TE2 suppression: bench backups must beat real FLEX/depth opportunity cost.
        if pos=="QB" and qb>=1:
            adj -= 16.0 if rnd<=14 else 8.0
            why.append("1-QB league QB2 bench tax")
        if pos=="TE" and te>=1 and flex_eligible>=6:
            adj -= 8.0
            why.append("TE2 must win FLEX/bench opportunity cost")
        # Kicker is mandatory, but preserve upside bench capital until the endgame.
        if pos=="K":
            k=int(counts.get("K",0))
            if k>=1:
                adj -= 50.0
                why.append("kicker slot already filled")
            elif rnd < total:
                adj -= 24.0
                why.append("required K reserved for final round")
            else:
                adj += 80.0
                why.append("final-round required kicker")
        # Do not force IDP before the offensive starting shell is built.
        if pos in ["DL","DB"] and flex_eligible<6 and rnd<=12:
            adj -= 8.0
            why.append("finish 2-FLEX offensive shell first")
        # V6.11: extra IDP is optional but merit-based. Tier 1-2 impact defenders
        # may compete with offensive bench depth; replacement extras keep the full tax.
        if pos in ("DL","DB") and ((pos=="DL" and dl>=1) or (pos=="DB" and db>=1)):
            _tier_v=pd.to_numeric(pd.Series([r.get("idp_quality_tier",5)]),errors="coerce").fillna(5).iloc[0]
            _vorp_v=pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0]
            if float(_tier_v)<=2 and float(_vorp_v)>=1.0 and rnd>=11:
                adj -= 4.0
                why.append("impact IDP3 bench competition")
            else:
                adj -= 30.0
                why.append("replacement extra IDP bench tax")
        if adj:
            x.at[idx,"evaluation_score"]=float(x.at[idx,"evaluation_score"])+adj
            if "roster_opportunity_adj" in x.columns:
                x.at[idx,"roster_opportunity_adj"]=float(x.at[idx,"roster_opportunity_adj"])+adj
            if "roster_opportunity_note" in x.columns and why:
                old=str(x.at[idx,"roster_opportunity_note"])
                x.at[idx,"roster_opportunity_note"]=(old+"; "+"; ".join(why)).strip("; ")
    return x



def apply_v933_context_quality_gate(df, roster, round_no, current_pick):
    """Context-card only gate: stop shallow-league IDPs from camping above useful offensive challengers.
    Does NOT change FINAL PICK evaluation_score.
    """
    x=df.copy()
    if x.empty:
        return x
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    x["context_score"]=pd.to_numeric(x["evaluation_score"],errors="coerce").fillna(-999.0)
    for idx,r in x.iterrows():
        if str(r.get("position","")) not in ["DL","DB"]:
            continue
        pos=str(r.get("position"))
        vorp=float(pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
        mp=pd.to_numeric(pd.Series([r.get("market_pick",np.nan)]),errors="coerce").iloc[0]
        _impact,_eligible,_evidence=_v934_idp_impact_score(r)
        penalty=0.0
        if not _eligible: penalty += 45.0
        if _impact < 6.0: penalty += 18.0
        # Exact league starts only one DL and one DB; an IDP context target must be actionable,
        # not merely a high raw model score.
        if int(round_no)<=10: penalty += 18.0
        elif int(round_no)<=12: penalty += 10.0
        elif int(round_no)<=14: penalty += 5.0
        if vorp < 1.50: penalty += 8.0
        # If market says the defender should still be there later, suppress repeated WAIT cards.
        if pd.notna(mp) and float(mp)-float(current_pick) >= 18: penalty += 10.0
        if pd.notna(mp) and float(mp)-float(current_pick) >= 36: penalty += 8.0
        # Never feature a second player at an already-filled one-IDP position.
        if int(counts.get(pos,0))>=1: penalty += 40.0
        x.at[idx,"context_score"]-=penalty
    return x

def apply_v931_idp_opportunity_gate(df, roster, round_no):
    """Compare IDPs directly with the best remaining offensive value after roster adjustments."""
    x=df.copy()
    if "evaluation_score" not in x.columns or x.empty:
        return x
    off=x[~x.position.isin(["DL","DB"])]
    if off.empty:
        return x
    best_off=float(pd.to_numeric(off.evaluation_score,errors="coerce").max())
    counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
    depth_thin=(counts.get("WR",0)<5) or (counts.get("RB",0)<4)
    idp_mask=x.position.isin(["DL","DB"])
    for idx,r in x.loc[idp_mask].iterrows():
        score=float(pd.to_numeric(pd.Series([r.get("evaluation_score",-999)]),errors="coerce").fillna(-999).iloc[0])
        vorp=float(pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
        _impact,_eligible,_evidence=_v934_idp_impact_score(r)
        penalty=0.0
        note=[]
        if not _eligible:
            penalty += 35.0
            note.append("fails IDP evidence gate")
        if _impact < 6.0:
            penalty += 12.0
            note.append("below IDP impact floor")
        if vorp < 0.75:
            penalty += 14.0
            note.append("fails IDP replacement-level gate")
        if depth_thin and int(round_no)<=15 and score < best_off-4.0:
            penalty += min(10.0, max(0.0,(best_off-score-4.0)*0.35))
            note.append("offensive opportunity cost")
        if penalty:
            x.at[idx,"evaluation_score"]=score-penalty
            old=str(x.at[idx,"roster_opportunity_note"]) if "roster_opportunity_note" in x.columns else ""
            x.at[idx,"roster_opportunity_note"]=(old+"; "+"; ".join(note)).strip("; ")
            if "roster_opportunity_adj" in x.columns:
                x.at[idx,"roster_opportunity_adj"]=float(x.at[idx,"roster_opportunity_adj"])-penalty
    # v9.40 evidence authority: failed IDP evidence cannot be rescued by roster need.
    if "idp_eligible" in x.columns:
        bad=x["position"].isin(["DL","DB"]) & (~x["idp_eligible"].fillna(False).astype(bool))
        x.loc[bad,"evaluation_score"]-=100.0
    return x



@st.cache_data(ttl=3600, show_spinner=False)
def _v645_razzball_projection_table():
    """Load current published 2026 season projections from Razzball."""
    import io
    url="https://football.razzball.com/projections/"
    headers={"User-Agent":"Mozilla/5.0 (Fantasy Edge projection refresh)"}
    r=requests.get(url,headers=headers,timeout=10)
    r.raise_for_status()
    tables=pd.read_html(io.StringIO(r.text))
    target=None
    for t in tables:
        tt=t.copy()
        if isinstance(tt.columns,pd.MultiIndex):
            tt.columns=[str(c[-1] if c[-1] and str(c[-1])!='nan' else c[0]).strip() for c in tt.columns]
        else:
            tt.columns=[str(c).strip() for c in tt.columns]
        cmap={str(c).strip().lower():c for c in tt.columns}
        if 'name' in cmap and 'pos' in cmap and 'ppr pts' in cmap:
            target=tt
            break
    if target is None or target.empty:
        raise ValueError('Razzball season projection table not found')
    cmap={str(c).strip().lower():c for c in target.columns}
    out=pd.DataFrame({
        'player':target[cmap['name']].astype(str).str.strip(),
        'position':target[cmap['pos']].astype(str).str.strip().map(canonical_position),
        'team':target[cmap.get('team',cmap['pos'])].astype(str).str.strip(),
        'std_points':pd.to_numeric(target[cmap.get('std pts')],errors='coerce') if cmap.get('std pts') else np.nan,
        'half_ppr_points':pd.to_numeric(target[cmap.get('1/2ppr pts')],errors='coerce') if cmap.get('1/2ppr pts') else np.nan,
        'ppr_points':pd.to_numeric(target[cmap['ppr pts']],errors='coerce'),
    })
    out=out[out['player'].ne('') & out['position'].isin(['QB','RB','WR','TE','K'])].copy()
    out['key']=out['player'].map(norm)
    out=out.dropna(subset=['ppr_points']).sort_values('ppr_points',ascending=False).drop_duplicates('key')
    out['projection_provider']='Razzball'
    return out.reset_index(drop=True)


@st.cache_data(ttl=3600, show_spinner=False)
def _v655_fantasypros_projection_table():
    """Secondary published-projection source for players Razzball does not match.

    FantasyPros exposes current draft-season FPTS tables by position.  This is
    intentionally a SECONDARY source.  We never synthesize fantasy points from
    rank when neither published projection feed contains the player.
    """
    import io
    rows=[]
    headers={"User-Agent":"Mozilla/5.0 (Fantasy Edge projection refresh)"}
    for pos in ['qb','rb','wr','te','k']:
        url=f"https://www.fantasypros.com/nfl/projections/{pos}.php?week=draft&scoring=PPR"
        try:
            r=requests.get(url,headers=headers,timeout=10)
            r.raise_for_status()
            tables=pd.read_html(io.StringIO(r.text))
        except Exception:
            continue
        for t in tables:
            tt=t.copy()
            if isinstance(tt.columns,pd.MultiIndex):
                tt.columns=[' '.join(str(x) for x in c if str(x)!='nan').strip() for c in tt.columns]
            else:
                tt.columns=[str(c).strip() for c in tt.columns]
            # Find a player/name column and an FPTS column regardless of header level.
            pcol=next((c for c in tt.columns if 'player' in str(c).lower()),None)
            fcol=next((c for c in tt.columns if 'fpts' in str(c).lower() or 'fantasy points' in str(c).lower()),None)
            if pcol is None or fcol is None:
                continue
            for _,rr in tt[[pcol,fcol]].iterrows():
                raw=str(rr[pcol]).strip()
                pts=pd.to_numeric(pd.Series([rr[fcol]]),errors='coerce').iloc[0]
                if not raw or pd.isna(pts):
                    continue
                # FantasyPros player cells commonly end in a 2-3 letter team code.
                name=re.sub(r'\\s+[A-Z]{2,3}$','',raw).strip()
                rows.append({'player':name,'position':pos.upper(),'ppr_points':float(pts)})
            break
    if not rows:
        return pd.DataFrame(columns=['player','position','ppr_points','key','projection_provider'])
    out=pd.DataFrame(rows)
    out['key']=out['player'].map(norm)
    out['projection_provider']='FantasyPros'
    out=out[out['key'].ne('')].sort_values('ppr_points',ascending=False).drop_duplicates('key')
    return out.reset_index(drop=True)


def _v645_apply_published_projections(board, ppr, teams, slots):
    """Overlay real published season projections and rebuild VORP/model values.

    V6.55 rule: no rank-derived or position-bucket fantasy-point fallbacks are
    allowed for offensive players. Razzball is primary, FantasyPros is secondary.
    If neither source publishes a projection for a player, projection and VORP
    are left missing and that player is excluded from recommendation scoring,
    while remaining visible in the full database.
    """
    if board is None or board.empty:
        return board,0,''
    errors=[]
    try:
        rz=_v645_razzball_projection_table()
    except Exception as e:
        rz=pd.DataFrame(); errors.append(f'Razzball {type(e).__name__}')
    try:
        fp=_v655_fantasypros_projection_table()
    except Exception as e:
        fp=pd.DataFrame(); errors.append(f'FantasyPros {type(e).__name__}')
    if (rz is None or rz.empty) and (fp is None or fp.empty):
        return board,0,'; '.join(errors) or 'published projection tables empty'

    x=board.copy()
    if 'key' not in x.columns:
        x['key']=x['player'].astype(str).map(norm)
    offensive=x['position'].isin(['QB','RB','WR','TE','K'])
    x['projection_available']=~offensive
    if 'projection_source' not in x.columns:
        x['projection_source']='Fantasy Edge IDP model'

    provider_parts=[]
    if isinstance(rz,pd.DataFrame) and len(rz):
        pr=rz.copy()
        _ppr=float(ppr)
        std=pd.to_numeric(pr.get('std_points'),errors='coerce')
        full=pd.to_numeric(pr.get('ppr_points'),errors='coerce')
        half=pd.to_numeric(pr.get('half_ppr_points'),errors='coerce')
        calc=std + _ppr*(full-std)
        calc=calc.where(calc.notna(), full if _ppr>=0.75 else half)
        pr['published_season_points']=calc
        pr['published_ppg']=pr['published_season_points']/17.0
        provider_parts.append(pr[['key','published_ppg','projection_provider']])
    if isinstance(fp,pd.DataFrame) and len(fp):
        pr2=fp.copy()
        # FantasyPros endpoint is requested with PPR scoring. For non-1.0 league
        # settings it remains a secondary fallback rather than inventing a rank curve.
        pr2['published_ppg']=pd.to_numeric(pr2['ppr_points'],errors='coerce')/17.0
        provider_parts.append(pr2[['key','published_ppg','projection_provider']])

    published=pd.concat(provider_parts,ignore_index=True) if provider_parts else pd.DataFrame()
    if published.empty:
        return board,0,'published projection tables empty'
    # Primary source wins when both contain the same player.
    published['_provider_order']=published['projection_provider'].map({'Razzball':0,'FantasyPros':1}).fillna(9)
    published=published.sort_values(['_provider_order']).dropna(subset=['published_ppg']).drop_duplicates('key',keep='first')
    mp=published.set_index('key')

    matched=offensive & x['key'].isin(mp.index)
    idx=x.index[matched]
    x.loc[idx,'projection']=x.loc[idx,'key'].map(mp['published_ppg']).astype(float).values
    x.loc[idx,'display_projection']=x.loc[idx,'projection']
    x.loc[idx,'last_ppg']=x.loc[idx,'projection']
    x.loc[idx,'prior_ppg']=x.loc[idx,'projection']
    x.loc[idx,'opp_pg']=x.loc[idx,'projection']
    x.loc[idx,'projection_source']=x.loc[idx,'key'].map(mp['projection_provider']).map(lambda v:f'{v} 2026 published season projection').values
    x.loc[idx,'projection_available']=True

    # Critical V6.55 truthfulness fix: wipe inherited position-bucket/rank-derived
    # estimates for unmatched offensive players. They stay visible but are not
    # allowed to masquerade as player-specific projections.
    unmatched=offensive & ~matched
    for c in ['projection','display_projection','vorp','display_vorp','replacement_ppg']:
        if c not in x.columns: x[c]=np.nan
        x.loc[unmatched,c]=np.nan
    x.loc[unmatched,'projection_source']='No published player-specific projection'
    x.loc[unmatched,'projection_available']=False

    t=max(int(teams),1)
    flex=float(slots.get('FLEX',0))
    alloc={'RB':0.38,'WR':0.55,'TE':0.07}
    replacement_slots={
        'QB':max(t*int(slots.get('QB',1)),t),
        'RB':max(int(round(t*(float(slots.get('RB',2))+flex*alloc['RB']))),t),
        'WR':max(int(round(t*(float(slots.get('WR',2))+flex*alloc['WR']))),t),
        'TE':max(int(round(t*(float(slots.get('TE',1))+flex*alloc['TE']))),t),
        'K':max(t*int(slots.get('K',1)),t),
    }
    repl={}
    for pos,n in replacement_slots.items():
        vals=pd.to_numeric(x.loc[x['position'].eq(pos) & x['projection_available'].fillna(False),'projection'],errors='coerce').dropna().sort_values(ascending=False).reset_index(drop=True)
        repl[pos]=float(vals.iloc[min(max(int(n)-1,0),len(vals)-1)]) if len(vals) else np.nan
    x.loc[matched,'replacement_ppg']=x.loc[matched,'position'].map(repl)
    x.loc[matched,'vorp']=pd.to_numeric(x.loc[matched,'projection'],errors='coerce')-pd.to_numeric(x.loc[matched,'replacement_ppg'],errors='coerce')
    x.loc[matched,'display_vorp']=x.loc[matched,'vorp']

    scarcity=x['position'].map({'QB':0.0,'RB':0.9,'WR':1.35,'TE':0.35,'K':-1.25}).fillna(0.0)
    prog=pd.to_numeric(x.get('progression',0),errors='coerce').fillna(0)
    reg=pd.to_numeric(x.get('regression',0),errors='coerce').fillna(0)
    cs=pd.to_numeric(x.get('consensus_strength',45),errors='coerce').fillna(45)
    pure=pd.to_numeric(x['vorp'],errors='coerce').fillna(0)*9.0 + pd.to_numeric(x['projection'],errors='coerce').fillna(0)*1.6 + prog*.12-reg*.10+scarcity
    x.loc[matched,'pure_model_score']=pure.loc[matched]
    x.loc[matched,'draft_score']=pure.loc[matched]+cs.loc[matched]*.10
    # Unprojected offense remains discoverable but cannot become a recommendation
    # winner from stale inherited scores.
    x.loc[unmatched,'draft_score']=np.nan
    x.loc[unmatched,'pure_model_score']=np.nan
    x['model_rank']=pd.to_numeric(x['draft_score'],errors='coerce').rank(method='min',ascending=False)
    x['display_model_rank']=x['model_rank']
    msg='; '.join(errors)
    return x,int(matched.sum()),msg

def _market_pick_series(df, teams):
    """V7.59 live/default champion market transform, certified by V7.58."""
    cr=pd.to_numeric(df["consensus_rank"],errors="coerce")
    out=cr.copy()
    idp=df["position"].isin(["DL","DB"])
    transformed=float(teams)*8 + (cr.loc[idp].fillna(40)-1)*2.0
    cap=cr.loc[idp].fillna(40) + float(teams)*8
    out.loc[idp]=np.minimum(transformed,cap)
    return out

def _board_with_vorp_variant(board, teams, slots, flex_alloc=None, vorp_weight=9.0):
    """Hypothetical valuation board used only by V7.29 matched calibration."""
    b=board.copy()
    teams=max(int(teams),1)
    flex=float(slots.get("FLEX",1))
    alloc={"RB":.38,"WR":.55,"TE":.07} if flex_alloc is None else {
        "RB":float(flex_alloc["RB"]),"WR":float(flex_alloc["WR"]),"TE":float(flex_alloc["TE"])
    }
    replacement_slots={
        "QB":max(teams*int(slots.get("QB",1)),teams),
        "RB":max(int(round(teams*(float(slots.get("RB",2))+flex*alloc["RB"]))),teams),
        "WR":max(int(round(teams*(float(slots.get("WR",2))+flex*alloc["WR"]))),teams),
        "TE":max(int(round(teams*(float(slots.get("TE",1))+flex*alloc["TE"]))),teams),
        "DL":max(teams*int(slots.get("DL",1)),teams),
        "DB":max(teams*int(slots.get("DB",1)),teams)
    }
    repl={}
    for p,n in replacement_slots.items():
        vals=pd.to_numeric(b.loc[b.position.eq(p),"projection"],errors="coerce").dropna().sort_values(ascending=False).reset_index(drop=True)
        repl[p]=float(vals.iloc[min(max(int(n)-1,0),len(vals)-1)]) if len(vals) else 0.0
    b["replacement_ppg"]=b.position.map(repl).fillna(0)
    b["vorp"]=pd.to_numeric(b.projection,errors="coerce").fillna(0)-b.replacement_ppg
    scarcity=b.position.map({"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"K":-1.25,"DL":-0.35,"DB":-0.45}).fillna(0)
    b["pure_model_score"]=(
        b.vorp*float(vorp_weight)
        +pd.to_numeric(b.projection,errors="coerce").fillna(0)*1.6
        +pd.to_numeric(b.progression,errors="coerce").fillna(0)*.12
        -pd.to_numeric(b.regression,errors="coerce").fillna(0)*.10
        +scarcity
    )
    b["model_rank"]=b.pure_model_score.rank(method="min",ascending=False)
    b["draft_score"]=b.pure_model_score+pd.to_numeric(b.consensus_strength,errors="coerce").fillna(45)*.10
    b["consensus_edge"]=b.consensus_rank-b.model_rank
    b.attrs["replacement_slots"]=replacement_slots
    return b


def _fast_benchmark_pool(board, teams=12):
    """Convert the static draft board to NumPy arrays once per benchmark run."""
    pool=board[board.position.isin(["QB","RB","WR","TE","DL","DB"])].copy().reset_index(drop=True)
    pos_names=np.array(["QB","RB","WR","TE","DL","DB"],dtype=object)
    pos_map={p:i for i,p in enumerate(pos_names)}
    pos_code=pool.position.map(pos_map).to_numpy(dtype=np.int8)
    consensus=pd.to_numeric(pool.consensus_rank,errors="coerce").to_numpy(dtype=float)
    market_pick=_market_pick_series(pool,teams).to_numpy(dtype=float)
    model_rank=pd.to_numeric(pool.model_rank,errors="coerce").to_numpy(dtype=float)
    draft_score=pd.to_numeric(pool.draft_score,errors="coerce").fillna(-1e9).to_numpy(dtype=float)
    projection=pd.to_numeric(pool.projection,errors="coerce").fillna(0).to_numpy(dtype=float)
    vorp=pd.to_numeric(pool.vorp,errors="coerce").fillna(0).to_numpy(dtype=float)
    replacement_ppg=pd.to_numeric(pool.replacement_ppg,errors="coerce").fillna(0).to_numpy(dtype=float)
    # Diagnostic replacement ranks by position, derived from the league's frozen
    # V7.25 replacement demand assumptions. These are not used in drafting.
    flex=float(1.0)
    replacement_demand={
        "QB":max(int(teams*1),int(teams)),
        "RB":max(int(round(teams*(2.0+flex*.38))),int(teams)),
        "WR":max(int(round(teams*(2.0+flex*.55))),int(teams)),
        "TE":max(int(round(teams*(1.0+flex*.07))),int(teams)),
        "DL":max(int(teams*1),int(teams)),
        "DB":max(int(teams*1),int(teams))
    }
    replacement_rank=np.array([replacement_demand.get(str(p),int(teams)) for p in pool.position],dtype=float)
    progression=pd.to_numeric(pool.progression,errors="coerce").fillna(0).to_numpy(dtype=float)
    regression=pd.to_numeric(pool.regression,errors="coerce").fillna(0).to_numpy(dtype=float)
    consensus_strength=pd.to_numeric(pool.consensus_strength,errors="coerce").fillna(45).to_numpy(dtype=float)
    pure_model_score=pd.to_numeric(pool.pure_model_score,errors="coerce").fillna(0).to_numpy(dtype=float)
    scarcity=np.array([{"QB":0.0,"RB":0.9,"WR":1.35,"TE":0.35,"K":-1.25,"DL":-0.35,"DB":-0.45}.get(str(p),0.0)
                       for p in pool.position],dtype=float)
    injury=np.array([_injury_severity(x) for x in pool.injury],dtype=np.int8)
    confidence=pd.to_numeric(pool.confidence,errors="coerce").fillna(.65).clip(.30,.95).to_numpy(dtype=float)
    return {"pool":pool,"pos_names":pos_names,"pos_code":pos_code,"consensus":consensus,
            "market_pick":market_pick,"model_rank":model_rank,"draft_score":draft_score,
            "projection":projection,"vorp":vorp,"replacement_ppg":replacement_ppg,
            "replacement_rank":replacement_rank,
            "progression":progression,"regression":regression,
            "consensus_strength":consensus_strength,"pure_model_score":pure_model_score,
            "scarcity":scarcity,"injury":injury,"confidence":confidence}


def _fast_roster_utility(fast, selected, slots, te_starter_vorp_mult=.90):
    """Small-array roster utility used by the benchmark engine."""
    if len(selected)==0: return 0.0
    idx=np.asarray(selected,dtype=int)
    pos=fast["pos_code"][idx]; proj=fast["projection"][idx]; vorp=fast["vorp"][idx]
    base=proj+0.70*np.clip(vorp,-5,None)
    used=np.zeros(len(idx),dtype=bool); total=0.0
    # Required starters by position.
    for code,pname in enumerate(["QB","RB","WR","TE","DL","DB"]):
        n=max(int(slots.get(pname,0)),0)
        loc=np.flatnonzero(pos==code)
        if not len(loc) or n<=0: continue
        order=loc[np.argsort(base[loc])[::-1]]
        take=order[:n]; used[take]=True
        _starter_vorp_mult=float(te_starter_vorp_mult) if pname=="TE" else .90
        total += float(np.sum(proj[take]+_starter_vorp_mult*vorp[take]))
    # FLEX from unused RB/WR/TE.
    flex_n=max(int(slots.get("FLEX",0)),0)
    loc=np.flatnonzero((~used)&np.isin(pos,[1,2,3]))
    if len(loc) and flex_n>0:
        order=loc[np.argsort(base[loc])[::-1]]; take=order[:flex_n]; used[take]=True
        total += float(np.sum(.92*proj[take]+.75*vorp[take]))
    # Bench insurance/upside utility.
    mults={0:[.14,.03],1:[.25,.15,.08,.03],2:[.40,.30,.20,.11,.06],3:[.16,.04],4:[.06],5:[.06]}
    for code in range(6):
        loc=np.flatnonzero((~used)&(pos==code))
        if not len(loc): continue
        order=loc[np.argsort(base[loc])[::-1]]
        for d,j in enumerate(order):
            arr=mults[code]; m=arr[d] if d<len(arr) else .02
            total += float(m*(proj[j]+.55*max(vorp[j],0)))
    return float(total)


def _fast_roster_role_snapshot(fast, selected, candidate, slots):
    """Diagnostic-only explanation of how one candidate is valued by roster utility."""
    before=[int(x) for x in selected]
    cand=int(candidate)
    after=before+[cand]

    current=_fast_roster_utility(fast,before,slots)
    new=_fast_roster_utility(fast,after,slots)
    delta=float(new-current)

    idx=np.asarray(after,dtype=int)
    pos=fast["pos_code"][idx]
    proj=fast["projection"][idx]
    vorp=fast["vorp"][idx]
    base=proj+0.70*np.clip(vorp,-5,None)
    used=np.zeros(len(idx),dtype=bool)
    roles=np.array(["bench"]*len(idx),dtype=object)

    for code,pname in enumerate(["QB","RB","WR","TE","DL","DB"]):
        n=max(int(slots.get(pname,0)),0)
        loc=np.flatnonzero(pos==code)
        if not len(loc) or n<=0:
            continue
        order=loc[np.argsort(base[loc])[::-1]]
        take=order[:n]
        used[take]=True
        roles[take]="starter"

    flex_n=max(int(slots.get("FLEX",0)),0)
    loc=np.flatnonzero((~used)&np.isin(pos,[1,2,3]))
    if len(loc) and flex_n>0:
        order=loc[np.argsort(base[loc])[::-1]]
        take=order[:flex_n]
        used[take]=True
        roles[take]="flex"

    j=len(idx)-1
    cand_role=str(roles[j])
    pcode=int(pos[j])
    pname=["QB","RB","WR","TE","DL","DB"][pcode]
    counts_before={name:int(np.sum(fast["pos_code"][before]==code)) if len(before) else 0
                   for code,name in enumerate(["QB","RB","WR","TE","DL","DB"])}

    direct_slots=int(slots.get(pname,0))
    direct_missing=max(direct_slots-counts_before.get(pname,0),0)
    flex_eligible=pname in ["RB","WR","TE"]

    if cand_role=="starter":
        role_proj=float(proj[j])
        role_vorp=.90*float(vorp[j])
    elif cand_role=="flex":
        role_proj=.92*float(proj[j])
        role_vorp=.75*float(vorp[j])
    else:
        mults={0:[.14,.03],1:[.25,.15,.08,.03],2:[.40,.30,.20,.11,.06],3:[.16,.04],4:[.06],5:[.06]}
        same_bench=np.flatnonzero((roles=="bench")&(pos==pcode))
        order=same_bench[np.argsort(base[same_bench])[::-1]]
        depth=list(order).index(j) if j in list(order) else 0
        arr=mults[pcode]
        mult=arr[depth] if depth<len(arr) else .02
        role_proj=mult*float(proj[j])
        role_vorp=mult*.55*max(float(vorp[j]),0)

    return {
        "utility_before":float(current),
        "utility_after":float(new),
        "utility_delta":delta,
        "role":cand_role,
        "position":pname,
        "projection":float(proj[j]),
        "vorp":float(vorp[j]),
        "replacement_ppg":float(fast["replacement_ppg"][cand]),
        "role_projection_component":float(role_proj),
        "role_vorp_component":float(role_vorp),
        "role_component_sum":float(role_proj+role_vorp),
        "direct_missing_before":int(direct_missing),
        "flex_eligible":bool(flex_eligible),
        "QB_before":counts_before["QB"],"RB_before":counts_before["RB"],
        "WR_before":counts_before["WR"],"TE_before":counts_before["TE"],
    }


def _fast_candidate_deltas(fast, selected, candidates, slots, exact_cap=56, te_starter_vorp_mult=.90):
    """Exact V7.3 utility on a bounded shortlist chosen from model + market value."""
    cand=np.asarray(candidates,dtype=int)
    if cand.size==0: return cand,np.array([],dtype=float)
    n=min(int(exact_cap),cand.size)
    ds=fast["draft_score"][cand]
    cr=fast["market_pick"][cand]
    cr2=np.where(np.isnan(cr),999.0,cr)
    k1=max(1,n//3); k2=max(1,n//3)
    ai=np.argpartition(-ds,min(k1-1,cand.size-1))[:k1]
    bi=np.argpartition(cr2,min(k2-1,cand.size-1))[:k2]
    # Reserve shortlist space for the best available players at each position.
    pi=[]
    pc=fast["pos_code"][cand]
    per=max(2,n//18)
    for code in range(6):
        loc=np.flatnonzero(pc==code)
        if loc.size:
            take=min(per,loc.size)
            best=loc[np.argpartition(-ds[loc],min(take-1,loc.size-1))[:take]]
            pi.extend(best.tolist())
    local=np.unique(np.concatenate([ai,bi,np.asarray(pi,dtype=int)]))
    if local.size>n:
        composite=(-ds[local])+0.05*cr2[local]
        local=local[np.argsort(composite)[:n]]
    short=cand[local]
    current=_fast_roster_utility(fast,selected,slots,te_starter_vorp_mult=te_starter_vorp_mult)
    delta=np.asarray([_fast_roster_utility(fast,selected+[int(c)],slots,te_starter_vorp_mult=te_starter_vorp_mult)-current for c in short],dtype=float)
    return short,delta

def independent_draft_grade_components(draft, teams=12):
    """Independent diagnostic components; excludes FE projection/VORP/regression/draft_score/utility weights."""
    if draft is None or len(draft)==0:
        return {"overall":0.0,"market_value":0.0,"starter_completion":0.0,"roster_balance":0.0,
                "availability":0.0,"avg_market_delta":0.0,"avg_reach":0.0,"avg_faller":0.0,
                "big_reaches":0,"missing_starters":6}
    d=draft.copy()
    market=pd.to_numeric(d.get("market_pick",d.get("consensus_rank")),errors="coerce")
    pick=pd.to_numeric(d["mock_pick"],errors="coerce")
    delta=(pick-market).fillna(0)
    market_value=float(.70*delta.clip(-18,18).mean())
    avg_reach=float(np.maximum(market-pick,0).fillna(0).mean())
    avg_faller=float(np.maximum(pick-market,0).fillna(0).mean())
    big_reaches=int(((market-pick)>=18).fillna(False).sum())
    counts=d.position.value_counts().to_dict()
    missing=sum(max(n-counts.get(p,0),0) for p,n in {"QB":1,"RB":2,"WR":2,"TE":1,"DL":1,"DB":1}.items())
    starter_completion=float(-8*missing)
    balance=0.0
    if counts.get("RB",0)<3: balance-=3
    if counts.get("WR",0)<3: balance-=3
    if counts.get("QB",0)>2: balance-=2*(counts["QB"]-2)
    if counts.get("TE",0)>2: balance-=1.5*(counts["TE"]-2)
    inj=d.injury.fillna("").astype(str).str.lower()
    availability=float(-8*inj.isin(["ir","pup","nfi","reserve/ir","reserve/pup"]).sum()-4*inj.isin(["out","suspended","susp"]).sum())
    overall=float(np.clip(70+market_value+starter_completion+balance+availability,0,100))
    return {"overall":overall,"market_value":market_value,"starter_completion":starter_completion,
            "roster_balance":float(balance),"availability":availability,"avg_market_delta":float(delta.mean()),
            "avg_reach":avg_reach,"avg_faller":avg_faller,"big_reaches":big_reaches,"missing_starters":int(missing)}

def independent_draft_grade(draft, teams=12):
    return independent_draft_grade_components(draft,teams)["overall"]


def draft_phase(round_no):
    r=int(round_no)
    if r<=3: return "R1-3"
    if r<=6: return "R4-6"
    if r<=10: return "R7-10"
    return "R11+"

def independent_phase_metrics(draft):
    """Pick-level independent market/timing attribution by draft phase.

    Uses only mock pick, market pick, round, position and model rank metadata for
    descriptive diagnostics. It does not feed back into draft decisions.
    """
    if draft is None or len(draft)==0:
        return pd.DataFrame(columns=[
            "Phase","Picks","Avg_market_delta","Avg_reach","Avg_faller",
            "Big_reaches","Avg_model_rank","QB","RB","WR","TE","DL","DB"
        ])

    d=draft.copy()
    d["mock_pick"]=pd.to_numeric(d["mock_pick"],errors="coerce")
    d["mock_round"]=pd.to_numeric(d["mock_round"],errors="coerce").fillna(0).astype(int)
    d["market_pick_num"]=pd.to_numeric(d.get("market_pick",d.get("consensus_rank")),errors="coerce")
    d["model_rank_num"]=pd.to_numeric(d.get("model_rank"),errors="coerce")
    d["Phase"]=d.mock_round.map(draft_phase)
    d["market_delta"]=(d.mock_pick-d.market_pick_num).fillna(0)   # + = faller captured
    d["reach"]=np.maximum(d.market_pick_num-d.mock_pick,0).fillna(0)
    d["faller"]=np.maximum(d.mock_pick-d.market_pick_num,0).fillna(0)
    d["big_reach"]=(d.reach>=18).astype(int)

    rows=[]
    for phase in ["R1-3","R4-6","R7-10","R11+"]:
        g=d[d.Phase.eq(phase)]
        counts=g.position.value_counts().to_dict() if len(g) else {}
        rows.append({
            "Phase":phase,
            "Picks":int(len(g)),
            "Avg_market_delta":float(g.market_delta.mean()) if len(g) else 0.0,
            "Avg_reach":float(g.reach.mean()) if len(g) else 0.0,
            "Avg_faller":float(g.faller.mean()) if len(g) else 0.0,
            "Big_reaches":int(g.big_reach.sum()) if len(g) else 0,
            "Avg_model_rank":float(g.model_rank_num.mean()) if len(g) and g.model_rank_num.notna().any() else np.nan,
            "QB":int(counts.get("QB",0)),"RB":int(counts.get("RB",0)),
            "WR":int(counts.get("WR",0)),"TE":int(counts.get("TE",0)),
            "DL":int(counts.get("DL",0)),"DB":int(counts.get("DB",0))
        })
    return pd.DataFrame(rows)

def _room_profile(name):
    return {
      "Consensus":(.95,0.0,0.0),
      "ADP-heavy":(.45,0.0,0.0),
      "Chaotic":(1.85,0.0,0.0),
      "Positional runs":(1.00,1.0,0.0),
      "Sharp/value":(.70,0.0,1.0)
    }.get(name,(1.0,0.0,0.0))

def simulate_mock_fast_pick7_recovery_trace(fast,teams,slot,rounds,slots,randomness=12,seed=None,room_profile="Consensus",intercept_enabled=False):
    out=simulate_mock_fast(
        fast,teams,slot,rounds,slots,randomness,True,seed,room_profile,
        late_wr_enabled=bool(intercept_enabled),late_wr_eval_deficit=8.0,
        late_wr_survival=.35,late_wr_slots=(7,)
    )
    keep=[c for c in ["mock_pick","mock_round","player","position","team","market_pick","market_delta","faller","reach","value"] if c in out.columns]
    return out,out[keep].copy()


def mid_round_pipeline_audit_snapshot(fast, candidate_idx, delta, edge, eval_score, chosen_global,
                                      current_pick, next_pick, randomness=12):
    """Diagnostic-only R4-6 decision audit. Never changes the selected player."""
    cand=np.asarray(candidate_idx,dtype=int)
    delta=np.asarray(delta,dtype=float)
    edge=np.asarray(edge,dtype=float)
    ev=np.asarray(eval_score,dtype=float)
    pool=fast["pool"]; pos=fast["pos_code"]; market=fast["market_pick"]
    model_rank=fast["model_rank"]; projection=fast["projection"]; vorp=fast["vorp"]
    replacement_ppg=fast["replacement_ppg"]; replacement_rank=fast["replacement_rank"]; progression=fast["progression"]
    regression=fast["regression"]; consensus_strength=fast["consensus_strength"]
    pure_model_score=fast["pure_model_score"]; scarcity=fast["scarcity"]
    draft_score=fast["draft_score"]
    chosen_global=int(chosen_global)

    loc=np.flatnonzero(cand==chosen_global)
    chosen_eval=float(ev[int(loc[0])]) if len(loc) else np.nan
    cmp=float(market[chosen_global]) if np.isfinite(market[chosen_global]) else np.nan
    cmr=float(model_rank[chosen_global]) if np.isfinite(model_rank[chosen_global]) else np.nan

    snap={
        "MR_Audit":1,
        "MR_Selected_player":str(pool.iloc[chosen_global].player),
        "MR_Selected_position":str(pool.iloc[chosen_global].position),
        "MR_Selected_eval":chosen_eval,
        "MR_Selected_market_pick":cmp,
        "MR_Selected_model_rank":cmr,
        "MR_Selected_projection":float(projection[chosen_global]),
        "MR_Selected_vorp":float(vorp[chosen_global]),
        "MR_Selected_reach":max(cmp-float(current_pick),0) if np.isfinite(cmp) else np.nan,
        "MR_Selected_faller":max(float(current_pick)-cmp,0) if np.isfinite(cmp) else np.nan,
        "MR_Selected_survival_est":survival_probability(cmp,next_pick,randomness) if np.isfinite(cmp) else np.nan,
        "MR_Market_best_player":"",
        "MR_Market_best_position":"",
        "MR_Market_best_pick":np.nan,
        "MR_Market_best_eval":np.nan,
        "MR_Market_best_survival_est":np.nan,
        "MR_Market_best_survived_actual":np.nan,
        "MR_Market_best_idx":None,
        "MR_Eval_best_player":"",
        "MR_Eval_best_position":"",
        "MR_Eval_best_market_pick":np.nan,
        "MR_Eval_best_score":np.nan,
        "MR_Eval_gap_selected_vs_market_best":np.nan,
        "MR_Market_gap_selected_vs_market_best":np.nan,
        "MR_Passed_faller_player":"",
        "MR_Passed_faller_position":"",
        "MR_Passed_faller_amount":0.0,
        "MR_Passed_faller_eval_gap":np.nan,
        "MR_Passed_faller_survival_est":np.nan,
        "MR_Passed_faller_survived_actual":np.nan,
        "MR_Passed_faller_idx":None,
        "MR42_Faller_draftscore_gap":np.nan,
        "MR42_Faller_rosterutility_gap":np.nan,
        "MR42_Faller_marketedge_gap":np.nan,
        "MR42_Faller_injury_gap":np.nan,
        "MR42_Faller_idp_penalty_gap":np.nan,
        "MR42_Faller_residual_noise_gap":np.nan,
        "MR42_Faller_vorp_gap":np.nan,
        "MR42_Faller_projection_gap":np.nan,
        "MR42_Faller_progression_gap":np.nan,
        "MR42_Faller_regression_gap":np.nan,
        "MR42_Faller_scarcity_gap":np.nan,
        "MR42_Faller_consensus_gap":np.nan,
        "MR42_Faller_component_sum":np.nan,
        "MR42_Faller_position":"",
        "MR43_TE_architecture_audit":0,
        "MR43_Selected_role":"",
        "MR43_Faller_role":"",
        "MR43_Selected_utility_delta":np.nan,
        "MR43_Faller_utility_delta":np.nan,
        "MR43_Utility_delta_gap":np.nan,
        "MR43_Selected_role_proj":np.nan,
        "MR43_Selected_role_vorp":np.nan,
        "MR43_Faller_role_proj":np.nan,
        "MR43_Faller_role_vorp":np.nan,
        "MR43_Selected_replacement_ppg":np.nan,
        "MR43_Faller_replacement_ppg":np.nan,
        "MR43_Replacement_gap":np.nan,
        "MR43_Selected_direct_missing":np.nan,
        "MR43_Faller_direct_missing":np.nan,
        "MR43_QB_before":np.nan,
        "MR43_RB_before":np.nan,
        "MR43_WR_before":np.nan,
        "MR43_TE_before":np.nan,
        "MR_Chosen_draftscore_component":np.nan,
        "MR_Chosen_rosterdelta_component":np.nan,
        "MR_Chosen_edge_component":np.nan,
        "MR_MarketBest_draftscore_component":np.nan,
        "MR_MarketBest_rosterdelta_component":np.nan,
        "MR_MarketBest_edge_component":np.nan,
        "MR_ComponentGap_draftscore":np.nan,
        "MR_ComponentGap_rosterdelta":np.nan,
        "MR_ComponentGap_edge":np.nan,
        "MR_Primary_component_driver":"",
        "MR_Positional_conflict":0,
        "MR_Conflict_alt_player":"",
        "MR_Conflict_alt_position":"",
        "MR_Conflict_eval_gap":np.nan,
        "MR_Conflict_draftscore_gap":np.nan,
        "MR_Conflict_rosterdelta_gap":np.nan,
        "MR_Conflict_edge_gap":np.nan,
        "MR_Conflict_market_gap":np.nan,
        "MR_Conflict_projection_raw_gap":np.nan,
        "MR_Conflict_replacement_raw_gap":np.nan,
        "MR_Conflict_vorp_raw_gap":np.nan,
        "MR_Conflict_progression_raw_gap":np.nan,
        "MR_Conflict_regression_raw_gap":np.nan,
        "MR_Conflict_scarcity_raw_gap":np.nan,
        "MR_Conflict_consensus_strength_raw_gap":np.nan,
        "MR_Conflict_vorp_component_gap":np.nan,
        "MR_Conflict_projection_component_gap":np.nan,
        "MR_Conflict_progression_component_gap":np.nan,
        "MR_Conflict_regression_component_gap":np.nan,
        "MR_Conflict_scarcity_component_gap":np.nan,
        "MR_Conflict_consensus_component_gap":np.nan,
        "MR_Conflict_pure_model_gap":np.nan,
        "MR_DraftScore_primary_driver":"",
        "MR28_Chosen_replacement_rank":np.nan,
        "MR28_Alt_replacement_rank":np.nan,
        "MR28_Base_replacement_gap":np.nan,
        "MR28_Base_vorp_gap":np.nan,
        "MR28_Alt_vorp_gap_flex_45_45_10":np.nan,
        "MR28_Alt_vorp_gap_flex_33_60_07":np.nan,
        "MR28_Alt_vorp_gap_flex_30_60_10":np.nan,
        "MR28_Alt_vorp_gap_equal_flex":np.nan,
        "MR28_Alt_vorp_gap_vorp7":np.nan,
        "MR28_Alt_vorp_gap_vorp6":np.nan,
    }

    if not len(cand):
        return snap

    # Highest FE evaluation candidate.
    ej=int(np.argmax(ev)); eg=int(cand[ej])
    snap.update({
        "MR_Eval_best_player":str(pool.iloc[eg].player),
        "MR_Eval_best_position":str(pool.iloc[eg].position),
        "MR_Eval_best_market_pick":float(market[eg]) if np.isfinite(market[eg]) else np.nan,
        "MR_Eval_best_score":float(ev[ej]),
    })

    # Earliest market-ranked candidate.
    cm=np.where(np.isnan(market[cand]),9999.0,market[cand])
    mj=int(np.argmin(cm)); mg=int(cand[mj])
    mmp=float(market[mg]) if np.isfinite(market[mg]) else np.nan
    msurv=survival_probability(mmp,next_pick,randomness) if np.isfinite(mmp) else np.nan
    snap.update({
        "MR_Market_best_player":str(pool.iloc[mg].player),
        "MR_Market_best_position":str(pool.iloc[mg].position),
        "MR_Market_best_pick":mmp,
        "MR_Market_best_eval":float(ev[mj]),
        "MR_Market_best_survival_est":msurv,
        "MR_Market_best_idx":mg,
        "MR_Eval_gap_selected_vs_market_best":chosen_eval-float(ev[mj]),
        "MR_Market_gap_selected_vs_market_best":cmp-mmp if np.isfinite(cmp) and np.isfinite(mmp) else np.nan,
    })

    # Exact V7.25 evaluation decomposition: chosen minus market-best.
    cj=int(loc[0]) if len(loc) else None
    if cj is not None:
        chosen_ds=.38*float(draft_score[chosen_global])
        chosen_rd=3.60*float(delta[cj])
        chosen_ed=.18*float(edge[cj])
        market_ds=.38*float(draft_score[mg])
        market_rd=3.60*float(delta[mj])
        market_ed=.18*float(edge[mj])
        gaps={
            "player_model/draft_score":chosen_ds-market_ds,
            "roster_marginal_utility":chosen_rd-market_rd,
            "model-vs-market_edge":chosen_ed-market_ed
        }
        snap.update({
            "MR_Chosen_draftscore_component":chosen_ds,
            "MR_Chosen_rosterdelta_component":chosen_rd,
            "MR_Chosen_edge_component":chosen_ed,
            "MR_MarketBest_draftscore_component":market_ds,
            "MR_MarketBest_rosterdelta_component":market_rd,
            "MR_MarketBest_edge_component":market_ed,
            "MR_ComponentGap_draftscore":gaps["player_model/draft_score"],
            "MR_ComponentGap_rosterdelta":gaps["roster_marginal_utility"],
            "MR_ComponentGap_edge":gaps["model-vs-market_edge"],
            "MR_Primary_component_driver":max(gaps,key=gaps.get)
        })

        # Focused conflict from V7.25: selected RB/TE while best WR/QB is available.
        if pos[chosen_global] in [1,3]:
            altloc=np.flatnonzero(np.isin(pos[cand],[0,2]))
            if len(altloc):
                # Compare against the strongest FE-evaluated WR/QB, not a forced market clone.
                aj=int(altloc[np.argmax(ev[altloc])]); ag=int(cand[aj])
                amp=float(market[ag]) if np.isfinite(market[ag]) else np.nan
                # Decompose the exact draft-score gap:
                # draft_score = VORP*9 + projection*1.6 + progression*.12
                #               - regression*.10 + scarcity + consensus_strength*.10
                vorp_raw=float(vorp[chosen_global]-vorp[ag])
                proj_raw=float(projection[chosen_global]-projection[ag])
                repl_raw=float(replacement_ppg[chosen_global]-replacement_ppg[ag])
                prog_raw=float(progression[chosen_global]-progression[ag])
                reg_raw=float(regression[chosen_global]-regression[ag])
                scarcity_raw=float(scarcity[chosen_global]-scarcity[ag])
                cons_raw=float(consensus_strength[chosen_global]-consensus_strength[ag])

                components={
                    "VORP":9.0*vorp_raw,
                    "projection":1.6*proj_raw,
                    "progression":.12*prog_raw,
                    "regression":-.10*reg_raw,
                    "positional_scarcity":scarcity_raw,
                    "consensus_reality_check":.10*cons_raw
                }
                primary=max(components,key=components.get)

                # V7.28 replacement/VORP baseline audit.
                base_gap=float(replacement_ppg[chosen_global]-replacement_ppg[ag])
                base_vorp_gap=float(vorp[chosen_global]-vorp[ag])

                scenarios={
                    "45_45_10":{"RB":.45,"WR":.45,"TE":.10},
                    "33_60_07":{"RB":.33,"WR":.60,"TE":.07},
                    "30_60_10":{"RB":.30,"WR":.60,"TE":.10},
                    "equal":{"RB":1/3,"WR":1/3,"TE":1/3},
                }
                alt_vorp={}
                for skey,alloc in scenarios.items():
                    repl_map,_dem=_diagnostic_replacement_ppg(pool,int(max(1,len(pool)//max(len(pool.position.unique()),1))),alloc)
                    cp=str(pool.iloc[chosen_global].position); ap=str(pool.iloc[ag].position)
                    cv=float(projection[chosen_global]-repl_map.get(cp,0.0))
                    av=float(projection[ag]-repl_map.get(ap,0.0))
                    alt_vorp[skey]=cv-av

                snap.update({
                    "MR_Positional_conflict":1,
                    "MR_Conflict_alt_player":str(pool.iloc[ag].player),
                    "MR_Conflict_alt_position":str(pool.iloc[ag].position),
                    "MR_Conflict_eval_gap":chosen_eval-float(ev[aj]),
                    "MR_Conflict_draftscore_gap":.38*float(draft_score[chosen_global]-draft_score[ag]),
                    "MR_Conflict_rosterdelta_gap":3.60*float(delta[cj]-delta[aj]),
                    "MR_Conflict_edge_gap":.18*float(edge[cj]-edge[aj]),
                    "MR_Conflict_market_gap":cmp-amp if np.isfinite(cmp) and np.isfinite(amp) else np.nan,
                    "MR_Conflict_projection_raw_gap":proj_raw,
                    "MR_Conflict_replacement_raw_gap":repl_raw,
                    "MR_Conflict_vorp_raw_gap":vorp_raw,
                    "MR_Conflict_progression_raw_gap":prog_raw,
                    "MR_Conflict_regression_raw_gap":reg_raw,
                    "MR_Conflict_scarcity_raw_gap":scarcity_raw,
                    "MR_Conflict_consensus_strength_raw_gap":cons_raw,
                    "MR_Conflict_vorp_component_gap":.38*components["VORP"],
                    "MR_Conflict_projection_component_gap":.38*components["projection"],
                    "MR_Conflict_progression_component_gap":.38*components["progression"],
                    "MR_Conflict_regression_component_gap":.38*components["regression"],
                    "MR_Conflict_scarcity_component_gap":.38*components["positional_scarcity"],
                    "MR_Conflict_consensus_component_gap":.38*components["consensus_reality_check"],
                    "MR_Conflict_pure_model_gap":float(pure_model_score[chosen_global]-pure_model_score[ag]),
                    "MR_DraftScore_primary_driver":primary,
                    "MR28_Chosen_replacement_rank":float(replacement_rank[chosen_global]),
                    "MR28_Alt_replacement_rank":float(replacement_rank[ag]),
                    "MR28_Base_replacement_gap":base_gap,
                    "MR28_Base_vorp_gap":base_vorp_gap,
                    "MR28_Alt_vorp_gap_flex_45_45_10":float(alt_vorp["45_45_10"]),
                    "MR28_Alt_vorp_gap_flex_33_60_07":float(alt_vorp["33_60_07"]),
                    "MR28_Alt_vorp_gap_flex_30_60_10":float(alt_vorp["30_60_10"]),
                    "MR28_Alt_vorp_gap_equal_flex":float(alt_vorp["equal"]),
                    "MR28_Alt_vorp_gap_vorp7":base_vorp_gap*(7.0/9.0),
                    "MR28_Alt_vorp_gap_vorp6":base_vorp_gap*(6.0/9.0),
                })

    # Best passed faller: most picks past market among non-selected candidates.
    falls=float(current_pick)-market[cand]
    falls=np.where(np.isnan(falls),-9999.0,falls)
    falls[cand==chosen_global]=-9999.0
    fj=int(np.argmax(falls))
    if falls[fj] > 0:
        fg=int(cand[fj]); fmp=float(market[fg])
        fsurv=survival_probability(fmp,next_pick,randomness)
        total_gap=chosen_eval-float(ev[fj])
        cj=int(loc[0]) if len(loc) else None
        if cj is not None:
            ds_gap=.38*float(draft_score[chosen_global]-draft_score[fg])
            ru_gap=3.60*float(delta[cj]-delta[fj])
            edge_gap=.18*float(edge[cj]-edge[fj])

            # Injury contribution exactly as used by eval_score.
            def _inj_pen(code):
                return 12.0 if int(code)==2 else 2.5 if int(code)==1 else 0.0
            injury_gap=_inj_pen(fast["injury"][fg])-_inj_pen(fast["injury"][chosen_global])

            # Early IDP penalty contribution. R4-6 only in this audit.
            rnd=max(1,int((int(current_pick)-1)//max(12,1))+1)
            idp_c=(8-rnd)*2.2 if rnd<=7 and int(pos[chosen_global]) in [4,5] else 0.0
            idp_f=(8-rnd)*2.2 if rnd<=7 and int(pos[fg]) in [4,5] else 0.0
            idp_gap=idp_f-idp_c

            vorp_gap=.38*9.0*float(vorp[chosen_global]-vorp[fg])
            proj_gap=.38*1.6*float(projection[chosen_global]-projection[fg])
            prog_gap=.38*.12*float(progression[chosen_global]-progression[fg])
            reg_gap=.38*(-.10)*float(regression[chosen_global]-regression[fg])
            scarcity_gap=.38*float(scarcity[chosen_global]-scarcity[fg])
            cons_gap=.38*.10*float(consensus_strength[chosen_global]-consensus_strength[fg])

            known=ds_gap+ru_gap+edge_gap+injury_gap+idp_gap
            residual=total_gap-known
            component_sum=vorp_gap+proj_gap+prog_gap+reg_gap+scarcity_gap+cons_gap
        else:
            ds_gap=ru_gap=edge_gap=injury_gap=idp_gap=residual=np.nan
            vorp_gap=proj_gap=prog_gap=reg_gap=scarcity_gap=cons_gap=component_sum=np.nan

        snap.update({
            "MR_Passed_faller_player":str(pool.iloc[fg].player),
            "MR_Passed_faller_position":str(pool.iloc[fg].position),
            "MR_Passed_faller_amount":float(falls[fj]),
            "MR_Passed_faller_eval_gap":total_gap,
            "MR_Passed_faller_survival_est":fsurv,
            "MR_Passed_faller_idx":fg,
            "MR42_Faller_draftscore_gap":ds_gap,
            "MR42_Faller_rosterutility_gap":ru_gap,
            "MR42_Faller_marketedge_gap":edge_gap,
            "MR42_Faller_injury_gap":injury_gap,
            "MR42_Faller_idp_penalty_gap":idp_gap,
            "MR42_Faller_residual_noise_gap":residual,
            "MR42_Faller_vorp_gap":vorp_gap,
            "MR42_Faller_projection_gap":proj_gap,
            "MR42_Faller_progression_gap":prog_gap,
            "MR42_Faller_regression_gap":reg_gap,
            "MR42_Faller_scarcity_gap":scarcity_gap,
            "MR42_Faller_consensus_gap":cons_gap,
            "MR42_Faller_component_sum":component_sum,
            "MR42_Faller_position":str(pool.iloc[fg].position),
        })
    return snap


def _diagnostic_replacement_ppg(pool, teams, flex_alloc):
    """Return per-position replacement PPG under a hypothetical FLEX allocation.
    Diagnostic only; does not affect V7.25 drafting.
    """
    alloc={"RB":float(flex_alloc.get("RB",.38)),
           "WR":float(flex_alloc.get("WR",.55)),
           "TE":float(flex_alloc.get("TE",.07))}
    demand={
        "QB":max(int(teams),int(teams)),
        "RB":max(int(round(teams*(2.0+alloc["RB"]))),int(teams)),
        "WR":max(int(round(teams*(2.0+alloc["WR"]))),int(teams)),
        "TE":max(int(round(teams*(1.0+alloc["TE"]))),int(teams)),
        "DL":max(int(teams),int(teams)),
        "DB":max(int(teams),int(teams))
    }
    out={}
    for p,n in demand.items():
        vals=pd.to_numeric(pool.loc[pool.position.eq(p),"projection"],errors="coerce").dropna().sort_values(ascending=False).reset_index(drop=True)
        out[p]=float(vals.iloc[min(max(n-1,0),len(vals)-1)]) if len(vals) else 0.0
    return out,demand


def mid_round_pipeline_summary(draft):
    if draft is None or len(draft)==0 or "MR_Audit" not in draft.columns:
        return {}
    d=draft[pd.to_numeric(draft.MR_Audit,errors="coerce").fillna(0).eq(1)].copy()
    if d.empty: return {}

    market_pos=d.MR_Market_best_position.value_counts(normalize=True)
    selected_pos=d.MR_Selected_position.value_counts(normalize=True)
    faller_pos=d.MR_Passed_faller_position.value_counts(normalize=True)

    out={
        "MR_Audit_picks":int(len(d)),
        "MR_avg_selected_reach":float(pd.to_numeric(d.MR_Selected_reach,errors="coerce").mean()),
        "MR_avg_selected_faller":float(pd.to_numeric(d.MR_Selected_faller,errors="coerce").mean()),
        "MR_avg_market_gap_vs_market_best":float(pd.to_numeric(d.MR_Market_gap_selected_vs_market_best,errors="coerce").mean()),
        "MR_avg_eval_edge_vs_market_best":float(pd.to_numeric(d.MR_Eval_gap_selected_vs_market_best,errors="coerce").mean()),
        "MR_market_best_survival_actual":float(pd.to_numeric(d.MR_Market_best_survived_actual,errors="coerce").mean()),
        "MR_passed_faller_amount":float(pd.to_numeric(d.MR_Passed_faller_amount,errors="coerce").mean()),
        "MR_passed_faller_eval_gap":float(pd.to_numeric(d.MR_Passed_faller_eval_gap,errors="coerce").mean()),
        "MR_passed_faller_survival_actual":float(pd.to_numeric(d.MR_Passed_faller_survived_actual,errors="coerce").mean()),
        "MR_avg_component_draftscore_gap":float(pd.to_numeric(d.MR_ComponentGap_draftscore,errors="coerce").mean()),
        "MR_avg_component_rosterdelta_gap":float(pd.to_numeric(d.MR_ComponentGap_rosterdelta,errors="coerce").mean()),
        "MR_avg_component_edge_gap":float(pd.to_numeric(d.MR_ComponentGap_edge,errors="coerce").mean()),
        "MR_positional_conflict_rate":float(pd.to_numeric(d.MR_Positional_conflict,errors="coerce").mean()),
    }
    for p in ["QB","RB","WR","TE"]:
        out[f"MR_Selected_{p}_share"]=float(selected_pos.get(p,0))
        out[f"MR_MarketBest_{p}_share"]=float(market_pos.get(p,0))
        out[f"MR_PassedFaller_{p}_share"]=float(faller_pos.get(p,0))

    drivers=d.MR_Primary_component_driver.value_counts(normalize=True)
    for name in ["player_model/draft_score","roster_marginal_utility","model-vs-market_edge"]:
        safe=name.replace("/","_").replace("-","_")
        out[f"MR_driver_{safe}"]=float(drivers.get(name,0))

    conflict=d[pd.to_numeric(d.MR_Positional_conflict,errors="coerce").fillna(0).eq(1)]
    out["MR_conflict_count"]=int(len(conflict))
    out["MR_conflict_eval_gap"]=float(pd.to_numeric(conflict.MR_Conflict_eval_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_draftscore_gap"]=float(pd.to_numeric(conflict.MR_Conflict_draftscore_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_rosterdelta_gap"]=float(pd.to_numeric(conflict.MR_Conflict_rosterdelta_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_edge_gap"]=float(pd.to_numeric(conflict.MR_Conflict_edge_gap,errors="coerce").mean()) if len(conflict) else np.nan
    out["MR_conflict_market_gap"]=float(pd.to_numeric(conflict.MR_Conflict_market_gap,errors="coerce").mean()) if len(conflict) else np.nan

    # V7.27 player/draft-score internals.
    for col,key in [
        ("MR_Conflict_projection_raw_gap","MR27_projection_raw_gap"),
        ("MR_Conflict_replacement_raw_gap","MR27_replacement_raw_gap"),
        ("MR_Conflict_vorp_raw_gap","MR27_vorp_raw_gap"),
        ("MR_Conflict_progression_raw_gap","MR27_progression_raw_gap"),
        ("MR_Conflict_regression_raw_gap","MR27_regression_raw_gap"),
        ("MR_Conflict_scarcity_raw_gap","MR27_scarcity_raw_gap"),
        ("MR_Conflict_consensus_strength_raw_gap","MR27_consensus_strength_raw_gap"),
        ("MR_Conflict_vorp_component_gap","MR27_vorp_component_gap"),
        ("MR_Conflict_projection_component_gap","MR27_projection_component_gap"),
        ("MR_Conflict_progression_component_gap","MR27_progression_component_gap"),
        ("MR_Conflict_regression_component_gap","MR27_regression_component_gap"),
        ("MR_Conflict_scarcity_component_gap","MR27_scarcity_component_gap"),
        ("MR_Conflict_consensus_component_gap","MR27_consensus_component_gap"),
        ("MR_Conflict_pure_model_gap","MR27_pure_model_gap"),
    ]:
        out[key]=float(pd.to_numeric(conflict[col],errors="coerce").mean()) if len(conflict) else np.nan

    driver_counts=conflict.MR_DraftScore_primary_driver.value_counts(normalize=True) if len(conflict) else pd.Series(dtype=float)
    for name in ["VORP","projection","progression","regression","positional_scarcity","consensus_reality_check"]:
        out[f"MR27_driver_{name}"]=float(driver_counts.get(name,0))

    for col,key in [
        ("MR28_Chosen_replacement_rank","MR28_chosen_replacement_rank"),
        ("MR28_Alt_replacement_rank","MR28_alt_replacement_rank"),
        ("MR28_Base_replacement_gap","MR28_base_replacement_gap"),
        ("MR28_Base_vorp_gap","MR28_base_vorp_gap"),
        ("MR28_Alt_vorp_gap_flex_45_45_10","MR28_vorp_gap_45_45_10"),
        ("MR28_Alt_vorp_gap_flex_33_60_07","MR28_vorp_gap_33_60_07"),
        ("MR28_Alt_vorp_gap_flex_30_60_10","MR28_vorp_gap_30_60_10"),
        ("MR28_Alt_vorp_gap_equal_flex","MR28_vorp_gap_equal"),
        ("MR28_Alt_vorp_gap_vorp7","MR28_vorp_gap_weight7"),
        ("MR28_Alt_vorp_gap_vorp6","MR28_vorp_gap_weight6"),
    ]:
        out[key]=float(pd.to_numeric(conflict[col],errors="coerce").mean()) if len(conflict) else np.nan

    if len(conflict):
        altmix=conflict.MR_Conflict_alt_position.value_counts(normalize=True)
        out["MR_conflict_alt_WR_share"]=float(altmix.get("WR",0))
        out["MR_conflict_alt_QB_share"]=float(altmix.get("QB",0))
    else:
        out["MR_conflict_alt_WR_share"]=0.0
        out["MR_conflict_alt_QB_share"]=0.0
    return out


def simulate_mock_fast(fast, teams, slot, rounds, slots, randomness=12, model_user=True, seed=None,
                       room_profile="Consensus", wr_eval_deficit=10.0, wr_survival=.52, wr_enabled=True,
                       late_wr_enabled=False, late_wr_eval_deficit=8.0, late_wr_survival=.35,
                       late_wr_slots=(7,12), p12_dual_damp_enabled=False,
                       p12_player_weight=1.0, p12_roster_weight=1.0,
                       p12_faller_need_enabled=False, p12_faller_min=7.0,
                       p12_faller_eval_deficit=8.0, p12_need_reach=4.0,
                       p12_need_survival=.55, p12_te_utility_dedup_enabled=False,
                       p12_te_starter_vorp_mult=.90,
                       p12_te_gap_conditional_enabled=False,
                       p12_te_gap_threshold=55.97,
                       late_empirical_survival_enabled=False,
                       late_force_faller_round=0,
                       r7_dominance_override_enabled=True,
                       r5_dominance_override_enabled=False,
                       r2_dominance_override_enabled=False,
                       r3_dominance_override_enabled=False,
                       r11_13_offense_dominance_override_enabled=False,
                       late_sequence_variant="champion",
                       r2_generic_adaptation_enabled=True,
                       r4_generic_adaptation_enabled=False,
                       r3_causal_probe_enabled=False,
                       r3_qb_opportunity_cost_enabled=True):
    """NumPy benchmark engine. Decision rules match simulate_mock; Pandas is used only for the final 15-row roster."""
    rng=np.random.default_rng(seed)
    pool=fast["pool"]; pos=fast["pos_code"]; consensus=fast["consensus"]
    market_pick=fast["market_pick"]; injury=fast["injury"]; confidence=fast["confidence"]
    model_rank=fast["model_rank"]; draft_score=fast["draft_score"]
    n=len(pool)
    room_noise,room_run,room_value=_room_profile(room_profile)
    fallback=model_rank+rng.normal(0,8*room_noise,n)
    sim_cons=np.where(np.isnan(market_pick),fallback,market_pick)
    alive=np.ones(n,dtype=bool)
    counts=np.zeros(6,dtype=np.int16)
    user_idx=[]; user_pick=[]; user_round=[]; drafted_order=[]
    user_mr_diag=[]
    pending_market_idx=None; pending_market_diag=None
    pending_faller_idx=None; pending_faller_diag=None
    total=int(teams)*int(rounds)
    qb,rb,wr,te,dl,db=0,1,2,3,4,5

    for overall in range(1,total+1):
        round_no=(overall-1)//int(teams)+1
        pir=(overall-1)%int(teams)+1
        owner=pir if round_no%2 else int(teams)-pir+1
        idx=np.flatnonzero(alive)
        if idx.size==0: break

        if owner==int(slot):
            if pending_market_idx is not None and pending_market_diag is not None:
                user_mr_diag[pending_market_diag]["MR_Market_best_survived_actual"]=1.0 if alive[int(pending_market_idx)] else 0.0
                pending_market_idx=None; pending_market_diag=None
            if pending_faller_idx is not None and pending_faller_diag is not None:
                user_mr_diag[pending_faller_diag]["MR_Passed_faller_survived_actual"]=1.0 if alive[int(pending_faller_idx)] else 0.0
                pending_faller_idx=None; pending_faller_diag=None
            eligible=np.ones(idx.size,dtype=bool)
            eligible &= injury[idx] < 3  # IR/PUP/NFI are unavailable in draft recommendations.
            # Legal maximums only.
            if int(slots.get("QB",1))<=1 and counts[qb]>=2: eligible &= pos[idx]!=qb
            if int(slots.get("TE",1))<=1 and counts[te]>=2: eligible &= pos[idx]!=te
            if counts[dl]>=max(int(slots.get("DL",1)),1): eligible &= pos[idx]!=dl
            if counts[db]>=max(int(slots.get("DB",1)),1): eligible &= pos[idx]!=db
            if round_no<=7 and np.count_nonzero(~np.isin(pos[idx],[dl,db]))>=5:
                eligible &= ~np.isin(pos[idx],[dl,db])

            # Guarantee required starters only when picks are running out.
            missing_codes=[]
            for code,pname in enumerate(["QB","RB","WR","TE","DL","DB"]):
                missing_codes.extend([code]*max(int(slots.get(pname,0))-int(counts[code]),0))
            user_picks_left=int(rounds)-int(round_no)+1
            if missing_codes and user_picks_left<=len(missing_codes):
                force=np.isin(pos[idx],np.asarray(list(set(missing_codes)),dtype=int))
                if np.any(force): eligible &= force
            eidx=idx[eligible]
            if eidx.size==0: eidx=idx

            if model_user:
                # Core V7.3 architecture: actual marginal expected final-roster utility.
                _te_util_mult=.90
                if bool(p12_te_utility_dedup_enabled) and int(slot)==12 and 4<=round_no<=6:
                    _te_util_mult=float(p12_te_starter_vorp_mult)
                elif int(slot)==12 and 4<=round_no<=6:
                    # V7.50 PROMOTED CHAMPION RULE — frozen exactly from V7.47/V7.48/V7.49.
                    # Baseline .90 must select TE and the most-passed market faller's
                    # evaluation gap must be >= 55.97 before TE starter utility uses .30.
                    _base_sidx,_base_delta=_fast_candidate_deltas(
                        fast,user_idx,eidx,slots,exact_cap=56,te_starter_vorp_mult=.90
                    )
                    _base_cr=np.where(np.isnan(market_pick[_base_sidx]),float(overall),market_pick[_base_sidx])
                    _base_edge=np.clip(_base_cr-model_rank[_base_sidx],-24,24)
                    _base_edge=np.where(np.isin(pos[_base_sidx],[dl,db]),_base_edge*.45,_base_edge)
                    _base_noise=rng.normal(
                        0,(1.0-confidence[_base_sidx])*float(randomness)*0.30,size=_base_sidx.size
                    )
                    _base_eval=(0.38*draft_score[_base_sidx] + 3.60*_base_delta + 0.18*_base_edge)
                    _base_eval-=np.where(
                        injury[_base_sidx]==2,12.0,np.where(injury[_base_sidx]==1,2.5,0.0)
                    )
                    _base_eval+=_base_noise
                    if round_no<=7:
                        _base_eval-=np.where(
                            np.isin(pos[_base_sidx],[dl,db]),(8-round_no)*2.2,0
                        )
                    _base_nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                    _base_choice,_,_=execution_choice(
                        _base_eval,_base_cr,overall,_base_nxt,randomness
                    )
                    _base_global=int(_base_sidx[_base_choice])
                    _base_pos=str(pool.iloc[_base_global].position)
                    _falls=float(overall)-market_pick[_base_sidx]
                    _falls=np.where(np.isnan(_falls),-9999.0,_falls)
                    _falls[_base_choice]=-9999.0
                    _fj=int(np.argmax(_falls)) if len(_falls) else -1
                    _passed_gap=np.nan
                    if _fj>=0 and _falls[_fj]>0:
                        _passed_gap=float(_base_eval[_base_choice]-_base_eval[_fj])
                    if _base_pos=="TE" and pd.notna(_passed_gap) and _passed_gap>=55.97:
                        _te_util_mult=.30
                sidx,delta=_fast_candidate_deltas(fast,user_idx,eidx,slots,exact_cap=56,te_starter_vorp_mult=_te_util_mult)
                cr=np.where(np.isnan(market_pick[sidx]),float(overall),market_pick[sidx])
                edge=np.clip(cr-model_rank[sidx],-24,24)
                edge=np.where(np.isin(pos[sidx],[dl,db]),edge*.45,edge)

                # V7.9 PLAYER EVALUATION: who do we believe is best, independent of when to draft him?
                _eval_noise=rng.normal(0,(1.0-confidence[sidx])*float(randomness)*0.30,size=sidx.size)
                eval_score=(0.38*draft_score[sidx] + 3.60*delta + 0.18*edge)
                eval_score-=np.where(injury[sidx]==2,12.0,np.where(injury[sidx]==1,2.5,0.0))
                eval_score+=_eval_noise
                if round_no<=7:
                    eval_score-=np.where(np.isin(pos[sidx],[dl,db]),(8-round_no)*2.2,0)

                # V7.9 PICK EXECUTION: among our model targets, whose draft window is actually open now?
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                if bool(late_empirical_survival_enabled) and round_no>=11:
                    _late_surv=late_survival_probability_array_empirical(
                        cr,nxt,int(slot),int(round_no)
                    )
                    local_choice,_,_=execution_choice_with_survival(
                        eval_score,cr,overall,nxt,_late_surv
                    )
                else:
                    local_choice,_,_=execution_choice(eval_score,cr,overall,nxt,randomness)

                # V7.48.1 FIXED frozen discriminator.
                # First evaluate the normal .90 path using the real NumPy market arrays.
                # The feature is the same diagnostic used in V7.47:
                # selected TE evaluation minus the MOST-PASSED market faller's evaluation.
                if bool(p12_te_gap_conditional_enabled) and int(slot)==12 and 4<=round_no<=6:
                    _baseline_choice=int(local_choice)
                    _baseline_global=int(sidx[_baseline_choice])
                    _baseline_pos=str(pool.iloc[_baseline_global].position)

                    _falls=float(overall)-market_pick[sidx]
                    _falls=np.where(np.isnan(_falls),-9999.0,_falls)
                    _falls[_baseline_choice]=-9999.0
                    _fj=int(np.argmax(_falls)) if len(_falls) else -1

                    _passed_gap=np.nan
                    if _fj>=0 and _falls[_fj]>0:
                        _passed_gap=float(eval_score[_baseline_choice]-eval_score[_fj])

                    if _baseline_pos=="TE" and pd.notna(_passed_gap) and _passed_gap>=float(p12_te_gap_threshold):
                        # Recompute only marginal roster utility with TE starter VORP=.30.
                        # Candidate set, market edge, injury adjustment, and random noise stay identical.
                        _sidx30,_delta30=_fast_candidate_deltas(
                            fast,user_idx,eidx,slots,exact_cap=56,te_starter_vorp_mult=.30
                        )
                        # _fast_candidate_deltas is deterministic and should return the same shortlist,
                        # but remap defensively if its order ever changes.
                        _map30={int(g):float(d) for g,d in zip(_sidx30,_delta30)}
                        _delta30_aligned=np.asarray([_map30.get(int(g),float(delta[k])) for k,g in enumerate(sidx)],dtype=float)
                        eval_score=(0.38*draft_score[sidx] + 3.60*_delta30_aligned + 0.18*edge)
                        eval_score-=np.where(injury[sidx]==2,12.0,np.where(injury[sidx]==1,2.5,0.0))
                        eval_score+=_eval_noise
                        if round_no<=7:
                            eval_score-=np.where(np.isin(pos[sidx],[dl,db]),(8-round_no)*2.2,0)
                        delta=_delta30_aligned
                        local_choice,_,_=execution_choice(eval_score,cr,overall,nxt,randomness)

                # V7.39 calibration-only Pick-12 dual-driver damping.
                if bool(p12_dual_damp_enabled) and int(slot)==12 and 4<=round_no<=6 and int(pos[sidx][local_choice]) in [1,3]:
                    _wr=np.flatnonzero(pos[sidx]==2)
                    if len(_wr):
                        _wi=int(_wr[np.argmax(eval_score[_wr])])
                        _normal=int(local_choice)
                        _ds_gap=.38*float(draft_score[sidx][_normal]-draft_score[sidx][_wi])
                        _ru_gap=3.60*float(delta[_normal]-delta[_wi])
                        if _ds_gap>0 and _ru_gap>0:
                            _adj=np.asarray(eval_score,dtype=float).copy()
                            _adj[_normal]-=(1.0-float(p12_player_weight))*_ds_gap
                            _adj[_normal]-=(1.0-float(p12_roster_weight))*_ru_gap
                            local_choice=int(np.argmax(_adj))
                if wr_enabled:
                    local_choice,wr_scarcity,wr_diag=early_wr_scarcity_choice(
                        eval_score,cr,pos[sidx],overall,nxt,local_choice,
                        teams=int(teams),randomness=randomness,
                        max_eval_deficit=float(wr_eval_deficit),
                        max_wr_survival=float(wr_survival)
                    )
                else:
                    wr_scarcity=False
                    wr_diag={}
                local_choice,late_wr_intercept,late_wr_diag=late_slot_wr_conflict_choice(
                    eval_score,cr,pos[sidx],draft_score[sidx],fast["vorp"][sidx],
                    overall,nxt,local_choice,int(slot),teams=int(teams),randomness=randomness,
                    enabled=bool(late_wr_enabled),
                    max_eval_deficit=float(late_wr_eval_deficit),
                    max_wr_survival=float(late_wr_survival),
                    eligible_slots=late_wr_slots
                )
                local_choice,p12_faller_need,p12_faller_diag=pick12_faller_need_choice(
                    eval_score,cr,pos[sidx],overall,nxt,local_choice,
                    teams=int(teams),randomness=randomness,
                    enabled=bool(p12_faller_need_enabled),
                    min_fall=float(p12_faller_min),
                    max_eval_deficit=float(p12_faller_eval_deficit),
                    min_normal_reach=float(p12_need_reach),
                    max_normal_survival=float(p12_need_survival)
                )
                local_choice,_,_=faller_intercept_choice(
                    eval_score,cr,overall,local_choice,
                    teams=int(teams),rounds=int(rounds)
                )

                # V7.55 diagnostic counterfactual only:
                # at one specified late round, if V7.50 is reaching >=15 and a >=10-pick
                # passed market faller exists, force that faller. All subsequent picks
                # return to untouched V7.50 logic.
                if int(late_force_faller_round)==int(round_no) and round_no>=11:
                    _normal=int(local_choice)
                    _normal_reach=max(float(cr[_normal])-float(overall),0.0) if np.isfinite(cr[_normal]) else 0.0
                    _fall_amt=float(overall)-cr
                    _fall_amt=np.where(np.isnan(_fall_amt),-9999.0,_fall_amt)
                    _fall_amt[_normal]=-9999.0
                    _fj=int(np.argmax(_fall_amt)) if len(_fall_amt) else -1
                    if _normal_reach>=15.0 and _fj>=0 and float(_fall_amt[_fj])>=10.0:
                        local_choice=int(_fj)

                # V7.84 challenger-only R11-13 offense-only deep-faller dominance override.
                # Generic: no player, offensive position, draft slot, or room hard-coding.
                _r784_would_trigger=False
                _r784_best_global=None
                _r784_normal_global=None
                if 11<=round_no<=13:
                    _r84_normal=int(local_choice)
                    _r84_normal_global=int(sidx[_r84_normal])
                    _r784_normal_global=_r84_normal_global
                    _r84_market=float(cr[_r84_normal]) if np.isfinite(cr[_r84_normal]) else np.nan
                    _r84_delta=(_r84_market-float(overall)) if np.isfinite(_r84_market) else np.nan

                    if np.isfinite(_r84_delta) and _r84_delta < -30.0:
                        _r84_ids=eidx[eidx!=_r84_normal_global]
                        if len(_r84_ids):
                            _r84_off=_r84_ids[
                                ~pool.iloc[_r84_ids].position.isin(["DL","DB"]).to_numpy()
                            ]
                            if len(_r84_off):
                                _r84_dom=_r84_off[
                                    (draft_score[_r84_off] > draft_score[_r84_normal_global])
                                    & (fast["vorp"][_r84_off] > fast["vorp"][_r84_normal_global])
                                ]
                                if len(_r84_dom):
                                    _r84_ord=np.lexsort((
                                        np.where(np.isnan(market_pick[_r84_dom]),1e9,market_pick[_r84_dom]),
                                        -draft_score[_r84_dom]
                                    ))
                                    _r784_best_global=int(_r84_dom[_r84_ord[0]])
                                    _r784_would_trigger=True
                                    if bool(r11_13_offense_dominance_override_enabled):
                                        _r84_match=np.where(sidx==_r784_best_global)[0]
                                        if len(_r84_match):
                                            local_choice=int(_r84_match[0])

                # V7.91 challenger-only Round-2 generic adaptation rule.
                # Frozen pre-registered signature from V7.90:
                # alive+eligible alternative, BOTH higher frozen draft score and VORP,
                # effective market distance <=10 picks. No room/player/position/slot hard-coding.
                _r791_would_trigger=False
                _r791_best_global=None
                _r791_normal_global=None
                if round_no==2:
                    _r91_normal=int(local_choice)
                    _r91_normal_global=int(sidx[_r91_normal])
                    _r791_normal_global=_r91_normal_global
                    _r91_ids=eidx[eidx!=_r91_normal_global]
                    if len(_r91_ids):
                        _r91_market=np.where(np.isnan(market_pick[_r91_ids]),model_rank[_r91_ids],market_pick[_r91_ids])
                        _r91_distance=_r91_market-float(overall)
                        _r91_ok=(
                            (draft_score[_r91_ids] > draft_score[_r91_normal_global]) &
                            (fast["vorp"][_r91_ids] > fast["vorp"][_r91_normal_global]) &
                            (_r91_distance <= 10.0)
                        )
                        _r91_dom=_r91_ids[_r91_ok]
                        if len(_r91_dom):
                            _r91_ord=np.lexsort((
                                np.where(np.isnan(market_pick[_r91_dom]),1e9,market_pick[_r91_dom]),
                                -draft_score[_r91_dom]
                            ))
                            _r791_best_global=int(_r91_dom[_r91_ord[0]])
                            _r791_would_trigger=True
                            if bool(r2_generic_adaptation_enabled):
                                _r91_match=np.where(sidx==_r791_best_global)[0]
                                if len(_r91_match):
                                    local_choice=int(_r91_match[0])

                # V7.98 challenger-only Round-4 generic adaptation rule.
                # Pre-registered from V7.97: no room/player/position/slot hard-coding.
                # Trigger if a genuinely alive+eligible alternative has BOTH higher
                # frozen draft score and higher VORP, and effective market distance <=10.
                _r798_would_trigger=False
                _r798_best_global=None
                _r798_normal_global=None
                if round_no==4:
                    _r98_normal=int(local_choice)
                    _r98_normal_global=int(sidx[_r98_normal])
                    _r798_normal_global=_r98_normal_global
                    _r98_ids=eidx[eidx!=_r98_normal_global]

                    if len(_r98_ids):
                        _r98_market=np.where(np.isnan(market_pick[_r98_ids]),model_rank[_r98_ids],market_pick[_r98_ids])
                        _r98_distance=_r98_market-float(overall)
                        _r98_ok=(
                            (draft_score[_r98_ids] > draft_score[_r98_normal_global]) &
                            (fast["vorp"][_r98_ids] > fast["vorp"][_r98_normal_global]) &
                            (_r98_distance <= 10.0)
                        )
                        _r98_dom=_r98_ids[_r98_ok]
                        if len(_r98_dom):
                            _r98_ord=np.lexsort((
                                np.where(np.isnan(market_pick[_r98_dom]),1e9,market_pick[_r98_dom]),
                                -draft_score[_r98_dom]
                            ))
                            _r798_best_global=int(_r98_dom[_r98_ord[0]])
                            _r798_would_trigger=True
                            if bool(r4_generic_adaptation_enabled):
                                _r98_match=np.where(sidx==_r798_best_global)[0]
                                if len(_r98_match):
                                    local_choice=int(_r98_match[0])

                # V8.02 challenger-only Round-3 QB opportunity-cost rule.
                # Generic: only when the normal Round-3 selection is QB.
                # Alternative must be genuinely alive+eligible, non-QB,
                # BOTH higher frozen draft score and VORP, and within <=10 effective market picks.
                # No player, room, slot, or alternative-position hard-coding.
                _r802_would_trigger=False
                _r802_best_global=None
                _r802_normal_global=None

                if round_no==3:
                    _r802_normal=int(local_choice)
                    _r802_normal_global=int(sidx[_r802_normal])
                    _r802_normal_pos=str(pool.iloc[_r802_normal_global].position)

                    if _r802_normal_pos=="QB":
                        _r802_ids=eidx[eidx!=_r802_normal_global]
                        if len(_r802_ids):
                            _r802_nonqb=_r802_ids[
                                (pool.iloc[_r802_ids].position.astype(str)!="QB").to_numpy()
                            ]
                            if len(_r802_nonqb):
                                _r802_market=np.where(
                                    np.isnan(market_pick[_r802_nonqb]),
                                    model_rank[_r802_nonqb],
                                    market_pick[_r802_nonqb]
                                )
                                _r802_distance=_r802_market-float(overall)
                                _r802_ok=(
                                    (draft_score[_r802_nonqb] > draft_score[_r802_normal_global]) &
                                    (fast["vorp"][_r802_nonqb] > fast["vorp"][_r802_normal_global]) &
                                    (_r802_distance <= 10.0)
                                )
                                _r802_dom=_r802_nonqb[_r802_ok]

                                if len(_r802_dom):
                                    _r802_ord=np.lexsort((
                                        np.where(np.isnan(market_pick[_r802_dom]),1e9,market_pick[_r802_dom]),
                                        -draft_score[_r802_dom]
                                    ))
                                    _r802_best_global=int(_r802_dom[_r802_ord[0]])
                                    _r802_would_trigger=True

                                    if bool(r3_qb_opportunity_cost_enabled):
                                        _r802_match=np.where(sidx==_r802_best_global)[0]
                                        if len(_r802_match):
                                            local_choice=int(_r802_match[0])

                # V8.00 causal-probe-only Round-3 generic fork.
                # Same generic signature used for causal testing:
                # alive+eligible alternative, BOTH higher frozen draft score and VORP,
                # effective market distance <=10. No player/room/position/slot hard-coding.
                _r800_would_trigger=False
                _r800_best_global=None
                _r800_normal_global=None
                if round_no==3:
                    _r800_normal=int(local_choice)
                    _r800_normal_global=int(sidx[_r800_normal])
                    _r800_normal_global=int(_r800_normal_global)
                    _r800_ids=eidx[eidx!=_r800_normal_global]

                    if len(_r800_ids):
                        _r800_market=np.where(np.isnan(market_pick[_r800_ids]),model_rank[_r800_ids],market_pick[_r800_ids])
                        _r800_distance=_r800_market-float(overall)
                        _r800_ok=(
                            (draft_score[_r800_ids] > draft_score[_r800_normal_global]) &
                            (fast["vorp"][_r800_ids] > fast["vorp"][_r800_normal_global]) &
                            (_r800_distance <= 10.0)
                        )
                        _r800_dom=_r800_ids[_r800_ok]
                        if len(_r800_dom):
                            _r800_ord=np.lexsort((
                                np.where(np.isnan(market_pick[_r800_dom]),1e9,market_pick[_r800_dom]),
                                -draft_score[_r800_dom]
                            ))
                            _r800_best_global=int(_r800_dom[_r800_ord[0]])
                            _r800_would_trigger=True
                            if bool(r3_causal_probe_enabled):
                                _r800_match=np.where(sidx==_r800_best_global)[0]
                                if len(_r800_match):
                                    local_choice=int(_r800_match[0])

                # V7.80 challenger-only Round-3 true-board dominance override.
                # Generic: no player, position, slot, or room hard-coding.
                _r780_would_trigger=False
                _r780_best_global=None
                _r780_normal_global=None
                if round_no==3:
                    _r3_normal=int(local_choice)
                    _r3_normal_global=int(sidx[_r3_normal])
                    _r780_normal_global=_r3_normal_global
                    _r3_normal_market=float(cr[_r3_normal]) if np.isfinite(cr[_r3_normal]) else np.nan
                    _r3_normal_reach=(_r3_normal_market-float(overall)) if np.isfinite(_r3_normal_market) else np.nan

                    if np.isfinite(_r3_normal_reach) and _r3_normal_reach>10.0:
                        _r3_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r3_legal=(injury[eidx] < 3) & (_r3_market <= float(overall)+10.0)
                        _r3_ids=eidx[_r3_legal]
                        _r3_ids=_r3_ids[_r3_ids!=_r3_normal_global]

                        if len(_r3_ids):
                            _r3_dom=_r3_ids[
                                (draft_score[_r3_ids] > draft_score[_r3_normal_global])
                                & (fast["vorp"][_r3_ids] > fast["vorp"][_r3_normal_global])
                            ]
                            if len(_r3_dom):
                                _r3_ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_r3_dom]),1e9,market_pick[_r3_dom]),
                                    -draft_score[_r3_dom]
                                ))
                                _r780_best_global=int(_r3_dom[_r3_ord[0]])
                                _r780_would_trigger=True
                                if bool(r3_dominance_override_enabled):
                                    _r3_match=np.where(sidx==_r780_best_global)[0]
                                    if len(_r3_match):
                                        local_choice=int(_r3_match[0])

                # V7.77 challenger-only Round-2 true-board dominance override.
                # Generic: no player, position, slot, or room hard-coding.
                _r777_would_trigger=False
                _r777_best_global=None
                _r777_normal_global=None
                if round_no==2:
                    _r2_normal=int(local_choice)
                    _r2_normal_global=int(sidx[_r2_normal])
                    _r777_normal_global=_r2_normal_global
                    _r2_normal_market=float(cr[_r2_normal]) if np.isfinite(cr[_r2_normal]) else np.nan
                    _r2_normal_reach=(_r2_normal_market-float(overall)) if np.isfinite(_r2_normal_market) else np.nan
                    if np.isfinite(_r2_normal_reach) and _r2_normal_reach>10.0:
                        _r2_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r2_legal=(injury[eidx] < 3) & (_r2_market <= float(overall)+10.0)
                        _r2_ids=eidx[_r2_legal]
                        _r2_ids=_r2_ids[_r2_ids!=_r2_normal_global]
                        if len(_r2_ids):
                            _r2_dom=_r2_ids[
                                (draft_score[_r2_ids] > draft_score[_r2_normal_global])
                                & (fast["vorp"][_r2_ids] > fast["vorp"][_r2_normal_global])
                            ]
                            if len(_r2_dom):
                                _r2_ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_r2_dom]),1e9,market_pick[_r2_dom]),
                                    -draft_score[_r2_dom]
                                ))
                                _r777_best_global=int(_r2_dom[_r2_ord[0]])
                                _r777_would_trigger=True
                                if bool(r2_dominance_override_enabled):
                                    _r2_match=np.where(sidx==_r777_best_global)[0]
                                    if len(_r2_match):
                                        local_choice=int(_r2_match[0])

                # V7.71 challenger-only Round-5 dominance override.
                # No hard-coded player or slot. Fires only when the normal champion choice:
                # - is Round 5,
                # - reaches >10 picks versus effective market,
                # - and a truly alive+eligible, market-respecting alternative has
                #   BOTH higher frozen draft score and higher VORP.
                _r771_would_trigger=False
                _r771_best_global=None
                _r771_normal_global=None
                if round_no==5:
                    _r5_normal=int(local_choice)
                    _r5_normal_global=int(sidx[_r5_normal])
                    _r771_normal_global=_r5_normal_global
                    _r5_normal_market=float(cr[_r5_normal]) if np.isfinite(cr[_r5_normal]) else np.nan
                    _r5_normal_reach=(_r5_normal_market-float(overall)) if np.isfinite(_r5_normal_market) else np.nan

                    if np.isfinite(_r5_normal_reach) and _r5_normal_reach>10.0:
                        _r5_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r5_legal=(injury[eidx] < 3) & (_r5_market <= float(overall)+10.0)
                        _r5_ids=eidx[_r5_legal]
                        _r5_ids=_r5_ids[_r5_ids!=_r5_normal_global]

                        if len(_r5_ids):
                            _r5_dom=_r5_ids[
                                (draft_score[_r5_ids] > draft_score[_r5_normal_global])
                                & (fast["vorp"][_r5_ids] > fast["vorp"][_r5_normal_global])
                            ]
                            if len(_r5_dom):
                                _r5_ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_r5_dom]),1e9,market_pick[_r5_dom]),
                                    -draft_score[_r5_dom]
                                ))
                                _r771_best_global=int(_r5_dom[_r5_ord[0]])
                                _r771_would_trigger=True
                                if bool(r5_dominance_override_enabled):
                                    _r5_match=np.where(sidx==_r771_best_global)[0]
                                    if len(_r5_match):
                                        local_choice=int(_r5_match[0])

                # V7.67 production Round-7 dominance rule (promoted unchanged from V7.64-V7.66).
                # Compute the exact trigger once. V7.67 keeps it exposed diagnostically
                # so unchanged matched drafts can skip an unnecessary challenger rerun.
                _r766_would_trigger=False
                _r766_best_global=None
                _r766_normal_global=None
                if round_no==7:
                    _normal=int(local_choice)
                    _normal_global=int(sidx[_normal])
                    _r766_normal_global=_normal_global
                    _normal_market=float(cr[_normal]) if np.isfinite(cr[_normal]) else np.nan
                    _normal_reach=(_normal_market-float(overall)) if np.isfinite(_normal_market) else np.nan

                    if np.isfinite(_normal_reach) and _normal_reach>10.0:
                        _r7_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                        _r7_legal=(injury[eidx] < 3) & (_r7_market <= float(overall)+10.0)
                        _r7_ids=eidx[_r7_legal]
                        _r7_ids=_r7_ids[_r7_ids!=_normal_global]

                        if len(_r7_ids):
                            _dom=_r7_ids[
                                (draft_score[_r7_ids] > draft_score[_normal_global])
                                & (fast["vorp"][_r7_ids] > fast["vorp"][_normal_global])
                            ]
                            if len(_dom):
                                _ord=np.lexsort((
                                    np.where(np.isnan(market_pick[_dom]),1e9,market_pick[_dom]),
                                    -draft_score[_dom]
                                ))
                                _r766_best_global=int(_dom[_ord[0]])
                                _r766_would_trigger=True
                                if bool(r7_dominance_override_enabled):
                                    _match=np.where(sidx==_r766_best_global)[0]
                                    if len(_match):
                                        local_choice=int(_match[0])

                # V7.86 experimental late-sequence forcing.
                # Champion/default remains OFF->OFF->OFF->DB->DL for R11-15.
                # Variants only constrain broad OFF/DB/DL class by round; player choice inside the class
                # is still determined by the frozen engine's current local scores.
                if 11<=round_no<=15 and str(late_sequence_variant)!="champion":
                    _seq_map={
                        "db13": {11:"OFF",12:"OFF",13:"DB",14:"OFF",15:"DL"},
                        "db12": {11:"OFF",12:"DB",13:"OFF",14:"OFF",15:"DL"},
                    }
                    _target=_seq_map.get(str(late_sequence_variant),{}).get(int(round_no))
                    if _target:
                        _classes=np.array([
                            ("DB" if str(pool.iloc[int(g)].position)=="DB"
                             else ("DL" if str(pool.iloc[int(g)].position)=="DL" else "OFF"))
                            for g in sidx
                        ],dtype=object)
                        _cand=np.where(_classes==_target)[0]
                        if len(_cand):
                            # Stay inside the frozen engine: select best current eval_score among target-class options.
                            _best_local=int(_cand[int(np.argmax(eval_score[_cand]))])
                            local_choice=_best_local

                chosen=int(sidx[int(local_choice)])
                mr_diag={}

                # V8.06.3 exact true-board audit: eidx is the actual alive+eligible board
                # after all opponent selections preceding this user pick.
                _r8063_ids=eidx[eidx!=int(chosen)]
                if len(_r8063_ids):
                    _r8063_order=np.lexsort((
                        np.where(np.isnan(market_pick[_r8063_ids]),1e9,market_pick[_r8063_ids]),
                        -draft_score[_r8063_ids]
                    ))
                    _r8063_top=_r8063_ids[_r8063_order[:5]]
                else:
                    _r8063_top=np.asarray([],dtype=int)

                mr_diag.update({
                    "R8063_Audit":1,
                    "R8063_Actual_available_count":int(len(eidx)),
                    "R8063_QB_count_pre":int(counts[qb]),
                    "R8063_RB_count_pre":int(counts[rb]),
                    "R8063_WR_count_pre":int(counts[wr]),
                    "R8063_TE_count_pre":int(counts[te]),
                    "R8063_DL_count_pre":int(counts[dl]),
                    "R8063_DB_count_pre":int(counts[db]),
                })
                for _k in range(5):
                    if _k < len(_r8063_top):
                        _g=int(_r8063_top[_k])
                        _m=float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan
                        mr_diag.update({
                            f"R8063_Alt{_k+1}_player":str(pool.iloc[_g].player),
                            f"R8063_Alt{_k+1}_position":str(pool.iloc[_g].position),
                            f"R8063_Alt{_k+1}_market_pick":_m,
                            f"R8063_Alt{_k+1}_market_distance":(_m-float(overall)) if np.isfinite(_m) else np.nan,
                            f"R8063_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                            f"R8063_Alt{_k+1}_projection":float(fast["projection"][_g]),
                            f"R8063_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                            f"R8063_Alt{_k+1}_draft_score":float(draft_score[_g]),
                        })
                    else:
                        for _fld in ["market_pick","market_distance","model_rank","projection","vorp","draft_score"]:
                            mr_diag[f"R8063_Alt{_k+1}_{_fld}"]=np.nan
                        mr_diag[f"R8063_Alt{_k+1}_player"]=""
                        mr_diag[f"R8063_Alt{_k+1}_position"]=""

                # V7.89 measurement-only: R1-4 board-depletion snapshot.
                # Captures the best available frozen-score/VORP options at the exact user pick.
                if 1<=round_no<=4:
                    _r89_ids=eidx[eidx!=int(chosen)]
                    if len(_r89_ids):
                        _r89_score_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r89_ids]),1e9,market_pick[_r89_ids]),
                            -draft_score[_r89_ids]
                        ))
                        _r89_vorp_order=np.argsort(-fast["vorp"][_r89_ids])
                        _r89_best_score=int(_r89_ids[_r89_score_order[0]])
                        _r89_best_vorp=int(_r89_ids[_r89_vorp_order[0]])
                    else:
                        _r89_best_score=None
                        _r89_best_vorp=None

                    mr_diag.update({
                        "R789_Audit":1,
                        "R789_Actual_available_count":int(len(eidx)),
                        "R789_Best_score_player":str(pool.iloc[_r89_best_score].player) if _r89_best_score is not None else "",
                        "R789_Best_score_position":str(pool.iloc[_r89_best_score].position) if _r89_best_score is not None else "",
                        "R789_Best_score_market_pick":float(market_pick[_r89_best_score]) if _r89_best_score is not None and np.isfinite(market_pick[_r89_best_score]) else np.nan,
                        "R789_Best_score_vorp":float(fast["vorp"][_r89_best_score]) if _r89_best_score is not None else np.nan,
                        "R789_Best_score_draft_score":float(draft_score[_r89_best_score]) if _r89_best_score is not None else np.nan,

                        "R789_Best_vorp_player":str(pool.iloc[_r89_best_vorp].player) if _r89_best_vorp is not None else "",
                        "R789_Best_vorp_position":str(pool.iloc[_r89_best_vorp].position) if _r89_best_vorp is not None else "",
                        "R789_Best_vorp_market_pick":float(market_pick[_r89_best_vorp]) if _r89_best_vorp is not None and np.isfinite(market_pick[_r89_best_vorp]) else np.nan,
                        "R789_Best_vorp_vorp":float(fast["vorp"][_r89_best_vorp]) if _r89_best_vorp is not None else np.nan,
                        "R789_Best_vorp_draft_score":float(draft_score[_r89_best_vorp]) if _r89_best_vorp is not None else np.nan,
                    })

                if round_no==3:
                    mr_diag.update({
                        "R800_Would_trigger":1 if _r800_would_trigger else 0,
                        "R800_Normal_player":str(pool.iloc[int(_r800_normal_global)].player) if _r800_normal_global is not None else "",
                        "R800_Alt_player":str(pool.iloc[int(_r800_best_global)].player) if _r800_best_global is not None else "",
                        "R800_Alt_position":str(pool.iloc[int(_r800_best_global)].position) if _r800_best_global is not None else "",
                    })

                if round_no==3:
                    mr_diag.update({
                        "R802_Would_trigger":1 if _r802_would_trigger else 0,
                        "R802_Normal_player":str(pool.iloc[int(_r802_normal_global)].player) if _r802_normal_global is not None else "",
                        "R802_Alt_player":str(pool.iloc[int(_r802_best_global)].player) if _r802_best_global is not None else "",
                        "R802_Alt_position":str(pool.iloc[int(_r802_best_global)].position) if _r802_best_global is not None else "",
                    })

                # V7.99 measurement-only: Round-3 downstream mechanism audit.
                # Captures true-board alternatives and the post-R1-2 roster state.
                if round_no==3:
                    _r99_ids=eidx[eidx!=int(chosen)]
                    if len(_r99_ids):
                        _r99_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r99_ids]),1e9,market_pick[_r99_ids]),
                            -draft_score[_r99_ids]
                        ))
                        _r99_top=_r99_ids[_r99_order[:5]]
                    else:
                        _r99_top=np.asarray([],dtype=int)

                    mr_diag.update({
                        "R799_Audit":1,
                        "R799_QB_count_pre":int(counts[qb]),
                        "R799_RB_count_pre":int(counts[rb]),
                        "R799_WR_count_pre":int(counts[wr]),
                        "R799_TE_count_pre":int(counts[te]),
                        "R799_DL_count_pre":int(counts[dl]),
                        "R799_DB_count_pre":int(counts[db]),
                    })

                    for _k in range(5):
                        if _k < len(_r99_top):
                            _g=int(_r99_top[_k])
                            _m=float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan
                            mr_diag.update({
                                f"R799_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R799_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R799_Alt{_k+1}_market_pick":_m,
                                f"R799_Alt{_k+1}_market_distance":(_m-float(overall)) if np.isfinite(_m) else np.nan,
                                f"R799_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R799_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R799_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R799_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R799_Alt{_k+1}_player":"",
                                f"R799_Alt{_k+1}_position":"",
                                f"R799_Alt{_k+1}_market_pick":np.nan,
                                f"R799_Alt{_k+1}_market_distance":np.nan,
                                f"R799_Alt{_k+1}_model_rank":np.nan,
                                f"R799_Alt{_k+1}_projection":np.nan,
                                f"R799_Alt{_k+1}_vorp":np.nan,
                                f"R799_Alt{_k+1}_draft_score":np.nan,
                            })

                # V7.96 measurement-only: Round-4 true-board failure mechanism audit.
                if round_no==4:
                    _r4_ids=eidx[eidx!=int(chosen)]
                    if len(_r4_ids):
                        _r4_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r4_ids]),1e9,market_pick[_r4_ids]),
                            -draft_score[_r4_ids]
                        ))
                        _r4_top=_r4_ids[_r4_order[:5]]
                    else:
                        _r4_top=np.asarray([],dtype=int)

                    _pre_counts={p:int(counts[p]) for p in range(len(counts))}
                    mr_diag.update({
                        "R796_Audit":1,
                        "R796_Actual_available_count":int(len(eidx)),
                        "R796_QB_count_pre":int(counts[qb]),
                        "R796_RB_count_pre":int(counts[rb]),
                        "R796_WR_count_pre":int(counts[wr]),
                        "R796_TE_count_pre":int(counts[te]),
                        "R796_DL_count_pre":int(counts[dl]),
                        "R796_DB_count_pre":int(counts[db]),
                    })

                    for _k in range(5):
                        if _k < len(_r4_top):
                            _g=int(_r4_top[_k])
                            _m=float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan
                            mr_diag.update({
                                f"R796_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R796_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R796_Alt{_k+1}_market_pick":_m,
                                f"R796_Alt{_k+1}_market_distance":(_m-float(overall)) if np.isfinite(_m) else np.nan,
                                f"R796_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R796_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R796_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R796_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R796_Alt{_k+1}_player":"",
                                f"R796_Alt{_k+1}_position":"",
                                f"R796_Alt{_k+1}_market_pick":np.nan,
                                f"R796_Alt{_k+1}_market_distance":np.nan,
                                f"R796_Alt{_k+1}_model_rank":np.nan,
                                f"R796_Alt{_k+1}_projection":np.nan,
                                f"R796_Alt{_k+1}_vorp":np.nan,
                                f"R796_Alt{_k+1}_draft_score":np.nan,
                            })

                if round_no==5:
                    mr_diag.update({
                        "R771_Would_trigger":1 if _r771_would_trigger else 0,
                        "R771_Normal_player":str(pool.iloc[int(_r771_normal_global)].player) if _r771_normal_global is not None else "",
                        "R771_Best_alt_player":str(pool.iloc[int(_r771_best_global)].player) if _r771_best_global is not None else "",
                    })

                if round_no==4:
                    _r4_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                    _r4_legal=(injury[eidx] < 3) & (_r4_market <= float(overall)+10.0)
                    _r4_ids=eidx[_r4_legal]
                    _r4_ids=_r4_ids[_r4_ids!=int(chosen)]
                    if len(_r4_ids):
                        _r4_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r4_ids]),1e9,market_pick[_r4_ids]),
                            -draft_score[_r4_ids]
                        ))
                        _r4_top=_r4_ids[_r4_order[:5]]
                    else:
                        _r4_top=np.asarray([],dtype=int)

                    mr_diag.update({
                        "R769_Audit":1,
                        "R769_Actual_available_count":int(len(eidx)),
                        "R769_Market_respecting_count":int(len(_r4_ids)),
                    })
                    for _k in range(5):
                        if _k < len(_r4_top):
                            _g=int(_r4_top[_k])
                            mr_diag.update({
                                f"R769_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R769_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R769_Alt{_k+1}_market_pick":float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan,
                                f"R769_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R769_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R769_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R769_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R769_Alt{_k+1}_player":"",
                                f"R769_Alt{_k+1}_position":"",
                                f"R769_Alt{_k+1}_market_pick":np.nan,
                                f"R769_Alt{_k+1}_model_rank":np.nan,
                                f"R769_Alt{_k+1}_projection":np.nan,
                                f"R769_Alt{_k+1}_vorp":np.nan,
                                f"R769_Alt{_k+1}_draft_score":np.nan,
                            })

                # V7.70 measurement-only: true Round-5 board after all opponent picks.
                if round_no==5:
                    _r5_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                    _r5_legal=(injury[eidx] < 3) & (_r5_market <= float(overall)+10.0)
                    _r5_ids=eidx[_r5_legal]
                    _r5_ids=_r5_ids[_r5_ids!=int(chosen)]
                    if len(_r5_ids):
                        _r5_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r5_ids]),1e9,market_pick[_r5_ids]),
                            -draft_score[_r5_ids]
                        ))
                        _r5_top=_r5_ids[_r5_order[:5]]
                    else:
                        _r5_top=np.asarray([],dtype=int)
                    mr_diag.update({
                        "R770_Audit":1,
                        "R770_Actual_available_count":int(len(eidx)),
                        "R770_Market_respecting_count":int(len(_r5_ids)),
                    })
                    for _k in range(5):
                        if _k < len(_r5_top):
                            _g=int(_r5_top[_k])
                            mr_diag.update({
                                f"R770_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R770_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R770_Alt{_k+1}_market_pick":float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan,
                                f"R770_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R770_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R770_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R770_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R770_Alt{_k+1}_player":"",
                                f"R770_Alt{_k+1}_position":"",
                                f"R770_Alt{_k+1}_market_pick":np.nan,
                                f"R770_Alt{_k+1}_model_rank":np.nan,
                                f"R770_Alt{_k+1}_projection":np.nan,
                                f"R770_Alt{_k+1}_vorp":np.nan,
                                f"R770_Alt{_k+1}_draft_score":np.nan,
                            })

                if round_no==7:
                    mr_diag.update({
                        "R766_Would_trigger":1 if _r766_would_trigger else 0,
                        "R766_Normal_player":str(pool.iloc[int(_r766_normal_global)].player) if _r766_normal_global is not None else "",
                        "R766_Best_alt_player":str(pool.iloc[int(_r766_best_global)].player) if _r766_best_global is not None else "",
                    })

                # V7.63 diagnostic-only: capture the TRUE Round-7 board state after all opponent picks.
                # eidx is the actual alive+eligible player set at this exact user pick.
                if round_no==7:
                    _r7_market=np.where(np.isnan(market_pick[eidx]),model_rank[eidx],market_pick[eidx])
                    _r7_legal=(injury[eidx] < 3) & (_r7_market <= float(overall)+10.0)
                    _r7_ids=eidx[_r7_legal]
                    _r7_ids=_r7_ids[_r7_ids!=int(chosen)]
                    if len(_r7_ids):
                        _r7_order=np.lexsort((
                            np.where(np.isnan(market_pick[_r7_ids]),1e9,market_pick[_r7_ids]),
                            -draft_score[_r7_ids]
                        ))
                        _r7_top=_r7_ids[_r7_order[:5]]
                    else:
                        _r7_top=np.asarray([],dtype=int)

                    mr_diag.update({
                        "R763_Audit":1,
                        "R763_Actual_available_count":int(len(eidx)),
                        "R763_Market_respecting_count":int(len(_r7_ids)),
                    })
                    for _k in range(5):
                        if _k < len(_r7_top):
                            _g=int(_r7_top[_k])
                            mr_diag.update({
                                f"R763_Alt{_k+1}_player":str(pool.iloc[_g].player),
                                f"R763_Alt{_k+1}_position":str(pool.iloc[_g].position),
                                f"R763_Alt{_k+1}_market_pick":float(market_pick[_g]) if np.isfinite(market_pick[_g]) else np.nan,
                                f"R763_Alt{_k+1}_model_rank":float(model_rank[_g]) if np.isfinite(model_rank[_g]) else np.nan,
                                f"R763_Alt{_k+1}_projection":float(fast["projection"][_g]),
                                f"R763_Alt{_k+1}_vorp":float(fast["vorp"][_g]),
                                f"R763_Alt{_k+1}_draft_score":float(draft_score[_g]),
                            })
                        else:
                            mr_diag.update({
                                f"R763_Alt{_k+1}_player":"",
                                f"R763_Alt{_k+1}_position":"",
                                f"R763_Alt{_k+1}_market_pick":np.nan,
                                f"R763_Alt{_k+1}_model_rank":np.nan,
                                f"R763_Alt{_k+1}_projection":np.nan,
                                f"R763_Alt{_k+1}_vorp":np.nan,
                                f"R763_Alt{_k+1}_draft_score":np.nan,
                            })

                if 4<=round_no<=6 or round_no>=11:
                    _existing_diag=dict(mr_diag)
                    mr_diag=mid_round_pipeline_audit_snapshot(
                        fast,sidx,delta,edge,eval_score,chosen,overall,nxt,randomness
                    )
                    mr_diag.update(_existing_diag)
                    if int(slot)==12 and str(mr_diag.get("MR_Selected_position",""))=="TE" and str(mr_diag.get("MR_Passed_faller_position",""))=="WR":
                        _fg=mr_diag.get("MR_Passed_faller_idx",None)
                        if _fg is not None:
                            _sel=_fast_roster_role_snapshot(fast,user_idx,chosen,slots)
                            _fal=_fast_roster_role_snapshot(fast,user_idx,int(_fg),slots)
                            mr_diag.update({
                                "MR43_TE_architecture_audit":1,
                                "MR43_Selected_role":_sel["role"],
                                "MR43_Faller_role":_fal["role"],
                                "MR43_Selected_utility_delta":_sel["utility_delta"],
                                "MR43_Faller_utility_delta":_fal["utility_delta"],
                                "MR43_Utility_delta_gap":_sel["utility_delta"]-_fal["utility_delta"],
                                "MR43_Selected_role_proj":_sel["role_projection_component"],
                                "MR43_Selected_role_vorp":_sel["role_vorp_component"],
                                "MR43_Faller_role_proj":_fal["role_projection_component"],
                                "MR43_Faller_role_vorp":_fal["role_vorp_component"],
                                "MR43_Selected_replacement_ppg":_sel["replacement_ppg"],
                                "MR43_Faller_replacement_ppg":_fal["replacement_ppg"],
                                "MR43_Replacement_gap":_sel["replacement_ppg"]-_fal["replacement_ppg"],
                                "MR43_Selected_direct_missing":_sel["direct_missing_before"],
                                "MR43_Faller_direct_missing":_fal["direct_missing_before"],
                                "MR43_QB_before":_sel["QB_before"],
                                "MR43_RB_before":_sel["RB_before"],
                                "MR43_WR_before":_sel["WR_before"],
                                "MR43_TE_before":_sel["TE_before"],
                            })
            else:
                # Consensus baseline unchanged.
                mr_diag={}
                ce=eidx[injury[eidx]<3]
                if ce.size==0: ce=eidx
                noise=rng.normal(0,float(randomness)/3,ce.size)
                cr=np.where(np.isnan(market_pick[ce]),model_rank[ce],market_pick[ce])
                inj_cost=np.where(injury[ce]==2,28.0,np.where(injury[ce]==1,5.0,0.0))
                chosen=int(ce[int(np.argmin(cr+noise+inj_cost))])

            if 'mr_diag' not in locals(): mr_diag={}
            user_idx.append(chosen); user_pick.append(overall); user_round.append(round_no); user_mr_diag.append(mr_diag)
            if model_user and (4<=round_no<=6 or round_no>=11):
                if mr_diag.get("MR_Market_best_idx") is not None and int(mr_diag["MR_Market_best_idx"])!=int(chosen):
                    pending_market_idx=int(mr_diag["MR_Market_best_idx"]); pending_market_diag=len(user_mr_diag)-1
                if mr_diag.get("MR_Passed_faller_idx") is not None:
                    pending_faller_idx=int(mr_diag["MR_Passed_faller_idx"]); pending_faller_diag=len(user_mr_diag)-1
            counts[pos[chosen]]+=1
        else:
            # Same bounded-consensus opponent logic, without DataFrame allocation/sort.
            opp_idx=idx[injury[idx]<3]
            if opp_idx.size==0: opp_idx=idx
            base=sim_cons[opp_idx]
            window=max(18,min(45,int(16+overall*.12)))
            cand_mask=base<=overall+window
            cidx=opp_idx[cand_mask]
            if cidx.size==0:
                k=min(30,opp_idx.size)
                part=np.argpartition(base,k-1)[:k] if k<opp_idx.size else np.arange(opp_idx.size)
                cidx=opp_idx[part]
            sd=np.clip(4+sim_cons[cidx]/35,4,10)*room_noise
            opp=sim_cons[cidx]+rng.normal(0,sd)
            if room_value:
                agreement=np.clip(sim_cons[cidx]-model_rank[cidx],-20,20)
                opp-=.12*agreement
            if room_run and drafted_order:
                recent=[pos[x] for x in drafted_order[-4:]]
                vals,cts=np.unique(recent,return_counts=True)
                if len(cts) and int(np.max(cts))>=2:
                    run_code=int(vals[np.argmax(cts)])
                    opp-=np.where(pos[cidx]==run_code,3.0,0.0)
            opp+=np.where(injury[cidx]==2,28.0,np.where(injury[cidx]==1,5.0,0.0))
            if round_no<=7:
                opp+=np.where(np.isin(pos[cidx],[dl,db]),(8-round_no)*2.5,0)
            chosen=int(cidx[int(np.argmin(opp))])
        alive[chosen]=False
        drafted_order.append(chosen)

    if pending_market_idx is not None and pending_market_diag is not None:
        user_mr_diag[pending_market_diag]["MR_Market_best_survived_actual"]=1.0 if alive[int(pending_market_idx)] else 0.0
    if pending_faller_idx is not None and pending_faller_diag is not None:
        user_mr_diag[pending_faller_diag]["MR_Passed_faller_survived_actual"]=1.0 if alive[int(pending_faller_idx)] else 0.0
    roster=pool.iloc[user_idx].copy()
    roster["mock_pick"]=user_pick; roster["mock_round"]=user_round
    roster["market_pick"]=market_pick[user_idx]
    if len(user_mr_diag)==len(roster):
        md=pd.DataFrame(user_mr_diag,index=roster.index)
        for col in md.columns: roster[col]=md[col]
    return roster


def simulate_mock(board, teams, slot, rounds, slots, randomness=12, model_user=True, seed=None):
    """Original reference engine retained for interactive/debug use."""
    rng=np.random.default_rng(seed)
    pool=board.copy()
    pool=pool[pool.position.isin(["QB","RB","WR","TE","DL","DB"])].copy().reset_index(drop=True)
    pool["sim_consensus"]=pool.consensus_rank
    fallback=pool.model_rank + rng.normal(0,8,len(pool))
    pool["sim_consensus"]=pool.sim_consensus.fillna(fallback)
    alive=np.ones(len(pool),dtype=bool)
    user_rows=[]
    total=teams*rounds

    for overall in range(1,total+1):
        round_no=(overall-1)//teams+1
        pick_in_round=(overall-1)%teams+1
        owner_slot=pick_in_round if round_no%2 else teams-pick_in_round+1
        avail=pool.iloc[np.flatnonzero(alive)].copy()
        if avail.empty: break

        if owner_slot==slot:
            roster=pd.DataFrame(user_rows) if user_rows else board.iloc[0:0].copy()
            avail=draft_eligibility(avail,roster,round_no,rounds,slots)
            if avail.empty: avail=pool.iloc[np.flatnonzero(alive)].copy()
            avail["_construction_bonus"]=0.0
            rc=roster.position.value_counts().to_dict() if len(roster) else {}
            if rc.get("WR",0)<3: avail.loc[avail.position.eq("WR"),"_construction_bonus"]+=5.0
            elif rc.get("WR",0)==3: avail.loc[avail.position.eq("WR"),"_construction_bonus"]+=4.0
            elif rc.get("WR",0)==4: avail.loc[avail.position.eq("WR"),"_construction_bonus"]+=1.0
            if rc.get("RB",0)>=4: avail.loc[avail.position.eq("RB"),"_construction_bonus"]-=4.0
            if rc.get("RB",0)>=5: avail.loc[avail.position.eq("RB"),"_construction_bonus"]-=8.0
            avail["need"]=avail.position.map(lambda p: roster_need_for_mock(roster,p,slots))
            if model_user:
                avail["sim_score"]=avail.draft_score+avail["need"]+avail["_construction_bonus"]-np.maximum(overall-avail.consensus_rank.fillna(overall),0)*.08
                if round_no<=7: avail.loc[avail.position.isin(["DL","DB"]),"sim_score"] -= (8-round_no)*2.2
                counts=roster.position.value_counts().to_dict() if len(roster) else {}
                if counts.get("QB",0)>=1: avail.loc[avail.position.eq("QB"),"sim_score"] -= 10 if round_no<=10 else 5
                if counts.get("TE",0)>=1: avail.loc[avail.position.eq("TE"),"sim_score"] -= 8 if round_no<=10 else 3
                choice=avail.sort_values("sim_score",ascending=False).iloc[0]
            else:
                noise=rng.normal(0,randomness/3,len(avail)); avail["baseline"]=avail.sim_consensus+noise-avail["need"]*.25
                choice=avail.sort_values("baseline").iloc[0]
            rec=choice.to_dict(); rec["mock_pick"]=overall; rec["mock_round"]=round_no; user_rows.append(rec)
        else:
            base=avail.sim_consensus.fillna(avail.model_rank); window=max(18,min(45,int(16+overall*.12)))
            cand=avail[base<=overall+window].copy()
            if cand.empty: cand=avail.nsmallest(min(30,len(avail)),"sim_consensus")
            sd=np.clip(4+cand.sim_consensus.fillna(overall)/35,4,10); noise=rng.normal(0,sd)
            cand["opp_score"]=cand.sim_consensus.fillna(cand.model_rank)+noise
            if round_no<=7: cand.loc[cand.position.isin(["DL","DB"]),"opp_score"] += (8-round_no)*2.5
            choice=cand.sort_values("opp_score").iloc[0]
        alive[int(choice.name)]=False
    return pd.DataFrame(user_rows)


def _fast_local_draft_board():
    """
    Cold-start-safe board built entirely from the packaged certified production board.
    No external request is required for the initial dashboard render.
    """
    pb,_=load_v9_production()
    if pb is None or pb.empty:
        return pd.DataFrame()

    repl={"QB":16.0,"RB":8.2,"WR":7.6,"TE":5.6,"DL":6.2,"DB":5.9,"K":8.1}
    x=pd.DataFrame({
        "player":pb["Player"].astype(str),
        "position":pb["Position"].astype(str).map(canonical_position),
        "market_pick":pd.to_numeric(pb["Market_pick"],errors="coerce"),
        "consensus_rank":pd.to_numeric(pb["Market_pick"],errors="coerce"),
        "vorp":pd.to_numeric(pb["VORP"],errors="coerce").fillna(0.0),
        "draft_score":pd.to_numeric(pb["Draft_score"],errors="coerce").fillna(0.0),
        "model_rank":pd.to_numeric(pb["Model_rank"],errors="coerce"),
    })
    x["key"]=x["player"].map(norm)
    x["raw_position"]=x["position"]
    x["team"]="NFL"
    x["projection"]=x.apply(
        lambda r: float(repl.get(str(r["position"]),0.0))+float(r["vorp"]),axis=1
    )
    x["replacement_ppg"]=x["position"].map(repl).fillna(0.0)
    x["last_ppg"]=x["projection"]
    x["prior_ppg"]=x["projection"]
    x["opp_pg"]=x["projection"]
    x["progression"]=0.0
    x["regression"]=0.0
    x["scarcity"]=0.0
    x["pure_model_score"]=x["draft_score"]
    x["consensus_strength"]=(
        100.0*(1.0-np.log(x["consensus_rank"].clip(lower=1))/
               np.log(max(float(x["consensus_rank"].max()),250.0)))
    ).clip(0,100).fillna(45.0)
    x["confidence"]=0.78
    x["injury"]=""
    x["injury_severity"]=0
    x["injury_penalty"]=0.0
    x["role_score"]=0.0
    x["profile"]="Stable / neutral"
    x["age"]=np.nan
    x["exp"]=np.nan
    x["breakout"]=0.0
    x["decline"]=0.0
    x["waiver_score"]=x["projection"]*4.0+x["progression"]*.23-x["regression"]*.10
    x["display_projection"]=x["projection"]
    x["display_vorp"]=x["vorp"]
    x["display_model_rank"]=x["model_rank"]

    # V6.44: packaged top-300 fallback additions are real current-market players,
    # but they were not part of the original certified board. Tag them and use
    # slightly lower confidence rather than pretending they are fully certified.
    try:
        _v644_added=pd.read_csv(APP_DIR / "v644_added_players.csv")
        _v644_keys=set(_v644_added["Player"].astype(str).map(norm))
        _v644_mask=x["key"].isin(_v644_keys)
        x.loc[_v644_mask,"profile"]="Current top-300 fallback"
        x.loc[_v644_mask,"confidence"]=0.68
    except Exception:
        pass

    x["id"]="local:"+x["key"]
    x["identity_key"]=x["id"]+"|"+x["position"]

    kickers=[
        ("Brandon Aubrey","DAL"),("Ka'imi Fairbairn","HOU"),("Cameron Dicker","LAC"),
        ("Jason Myers","SEA"),("Cam Little","JAC"),("Eddy Pineiro","SF"),
        ("Evan McPherson","CIN"),("Tyler Loop","BAL"),("Chase McLaughlin","TB"),
        ("Harrison Mevis","LAR"),("Andy Borregales","NE"),("Cairo Santos","CHI"),
        ("Chris Boswell","PIT"),("Jake Bates","DET"),("Harrison Butker","KC"),
        ("Will Reichard","MIN"),("Wil Lutz","DEN"),("Charlie Smyth","NO"),
        ("Jake Elliott","PHI"),("Blake Grupe","IND"),("Tyler Bass","BUF"),
        ("Joey Slye","TEN"),("Chad Ryland","ARI"),("Nick Folk","ATL"),
        ("Zane Gonzalez","MIA"),
    ]
    n=len(kickers)
    projections=[]
    for rank in range(1,n+1):
        pct=1.0-(rank-1)/max(n-1,1)
        projections.append(7.35+2.15*pct)
    k12_proj=projections[min(11,n-1)]

    krows=[]
    for rank,((name,team),proj) in enumerate(zip(kickers,projections),1):
        vorp=float(proj-k12_proj)
        market=float(150+rank*1.8)
        ds=float(28.0-rank*0.35+vorp*4.0)
        krows.append({
            "player":name,"position":"K","raw_position":"K","team":team,
            "market_pick":market,"consensus_rank":market,"vorp":vorp,
            "draft_score":ds,"model_rank":float(160+rank),
            "key":norm(name),"projection":proj,"replacement_ppg":k12_proj,
            "last_ppg":proj,"prior_ppg":proj,"opp_pg":proj,
            "progression":0.0,"regression":0.0,"scarcity":-1.25,
            "pure_model_score":ds,"consensus_strength":max(50.0,88-rank),
            "confidence":0.76,"injury":"","injury_severity":0,
            "injury_penalty":0.0,"role_score":0.0,"profile":"Stable / neutral",
            "age":np.nan,"exp":np.nan,"breakout":0.0,"decline":0.0,
            "waiver_score":proj*4.0,"display_projection":proj,
            "display_vorp":vorp,"display_model_rank":float(160+rank),
            "id":"local-k:"+norm(name),"identity_key":"local-k:"+norm(name)+"|K",
        })

    x=pd.concat([x,pd.DataFrame(krows)],ignore_index=True,sort=False)
    x=attach_v9_production(x)
    x=_v938_unified_player_universe(x)
    return x.drop_duplicates(subset=["key"],keep="first").reset_index(drop=True)



def _v652_embedded_board_diagnostic():
    """Decode the authoritative embedded board directly, bypassing every Streamlit cache."""
    try:
        raw=gzip.decompress(base64.b64decode(_V651_BOARD_GZ_B64.encode("ascii")))
        d=pd.read_csv(io.BytesIO(raw))
        has_dobbins=bool(d["Player"].astype(str).str.contains("J.K. Dobbins",case=False,regex=False,na=False).any())
        return len(d), has_dobbins
    except Exception:
        return 0, False

state=load_state()
# V7.05 protected reconciliation: cloud is preferred only when it is not materially less complete.
# A populated local league is never replaced by an empty/truncated cloud payload.
_v705_prior=_v705_read_sync_status()
try:
    _row=_cloud_probe()
    _remote=_row.get("state") if isinstance(_row,dict) else None
    _cloud_updated=_row.get("updated_at","") if isinstance(_row,dict) else ""
    if isinstance(_remote,dict) and _remote:
        _suspicious,_why=_v705_state_is_suspicious(_remote,state)
        if _suspicious:
            # Protect local state and repair the cloud from the known-complete local league.
            _cloud_save(state)
            _verify=_cloud_probe()
            _v705_write_sync_status(True,"LOCAL_PROTECTED_AND_REPAIRED","",(_verify or {}).get("updated_at",""))
        else:
            state=_remote
            STATE.write_text(json.dumps(state,indent=2))
            _v705_write_sync_status(True,"CONNECTED_VERIFIED","",_cloud_updated)
    else:
        # No row exists: seed cloud from local.
        _cloud_save(state)
        _verify=_cloud_probe()
        _v705_write_sync_status(True,"SEEDED_FROM_LOCAL","",(_verify or {}).get("updated_at",""))
except Exception as _cloud_e:
    # Offline/error: remain on local state. Never discard local ownership.
    _v705_write_sync_status(False,"LOCAL_ONLY",repr(_cloud_e),"")

state["teams"]=12
# v9.44.1: authoritative league template. This intentionally overrides stale saved
# roster settings from older builds so Mock Draft Lab always reflects the real league.
state["roster_slots"]={
    "QB":1,"RB":2,"WR":2,"TE":1,"FLEX":2,"K":1,"DL":1,"DB":1,"BENCH":6
}
state["mock"]["rounds"]=17
state.setdefault("recommendation_history",[])

st.title("🏈 Fantasy Edge")
st.caption("Unified live-draft and mock-draft engine • 12-team snake • exact league construction")
st.caption("Fantasy Edge draft engine")
st.caption("⚡ Fast local startup active • external refresh is optional")

with st.sidebar:
    st.header("Yahoo league settings")
    teams=12
    st.number_input("Teams",12,12,12,disabled=True,help="Locked to your 12-team Yahoo league.")
    scoring=st.selectbox("Reception scoring",["PPR","Half PPR","Standard"],
                         index=0 if state["ppr"]==1 else 1 if state["ppr"]==.5 else 2)
    ppr={"PPR":1.0,"Half PPR":.5,"Standard":0.0}[scoring]
    pass_td=st.selectbox("Passing TD", [4,6], index=0 if int(state["pass_td"])==4 else 1)
    faab=st.number_input("FAAB budget",0,1000,int(state["faab"]))

    st.divider()
    st.subheader("IDP scoring")
    st.caption("Enter Yahoo's points for each defensive stat.")
    idp=state["idp"]
    idp["solo"]=st.number_input("Solo tackle",0.0,10.0,float(idp["solo"]),0.5)
    idp["assist"]=st.number_input("Assisted tackle",0.0,10.0,float(idp["assist"]),0.5)
    idp["sack"]=st.number_input("Sack",0.0,20.0,float(idp["sack"]),0.5)
    idp["tfl"]=st.number_input("Tackle for loss",0.0,10.0,float(idp["tfl"]),0.5)
    idp["qb_hit"]=st.number_input("QB hit",0.0,10.0,float(idp["qb_hit"]),0.5)
    idp["int"]=st.number_input("Interception",0.0,20.0,float(idp["int"]),0.5)
    idp["pd"]=st.number_input("Pass defended",0.0,10.0,float(idp["pd"]),0.5)
    idp["ff"]=st.number_input("Forced fumble",0.0,10.0,float(idp["ff"]),0.5)
    idp["fr"]=st.number_input("Fumble recovery",0.0,10.0,float(idp["fr"]),0.5)
    idp["def_td"]=st.number_input("Defensive TD",0.0,20.0,float(idp["def_td"]),0.5)
    idp["safety"]=st.number_input("Safety",0.0,10.0,float(idp["safety"]),0.5)

    st.divider()
    st.subheader("Starting roster")
    slots=state["roster_slots"]
    r1,r2=st.columns(2)
    slots["QB"]=r1.number_input("QB",0,4,int(slots["QB"]))
    slots["RB"]=r2.number_input("RB",0,6,int(slots["RB"]))
    slots["WR"]=r1.number_input("WR",0,6,int(slots["WR"]))
    slots["TE"]=r2.number_input("TE",0,4,int(slots["TE"]))
    slots["FLEX"]=r1.number_input("FLEX (RB/WR/TE)",0,4,int(slots["FLEX"]))
    slots["K"]=r2.number_input("Kicker",0,2,int(slots.get("K",1)))
    slots["DL"]=r1.number_input("DL",0,4,int(slots["DL"]))
    slots["DB"]=r2.number_input("DB",0,4,int(slots["DB"]))
    slots["BENCH"]=r1.number_input("Bench",0,10,int(slots.get("BENCH",6)))
    st.caption("League profile: 1 QB • 2 RB • 2 WR • 2 FLEX • 1 K • 1 DL • 1 DB • 6 bench. Kicker is reserved for the final roster slot and ranked by differentiated projection, market signal, and K-specific VORP.")

    state.update({"teams":teams,"ppr":ppr,"pass_td":pass_td,"faab":faab,"idp":idp,"roster_slots":slots})
    if st.button("Save all scoring settings"):
        save_state(state); st.success("Saved")

# Fast startup: render from the certified local board immediately.
_refresh_live=st.sidebar.checkbox(
    "Refresh external NFL data",
    value=False,
    help="Off = fastest/reliable startup using the packaged certified board. "
         "Turn on only when you want a full external data rebuild."
)

if _refresh_live:
    with st.spinner("Refreshing external NFL data…"):
        try:
            players=sleeper_players()
            hist=nfl_history()
            market=market_rankings(ppr)
            board=make_board(players,hist,market,ppr,pass_td,idp,teams,state["roster_slots"])
            board["market_pick"]=_market_pick_series(board,teams)
            board=attach_v9_production(board)
            board=_v938_unified_player_universe(board)
            board=apply_v92_injury_overlay(board,state)
            st.sidebar.success("External board refreshed")
        except Exception:
            st.sidebar.warning("External refresh failed; using certified local board.")
            players=pd.DataFrame()
            hist=pd.DataFrame()
            market=pd.DataFrame()
            board=_fast_local_draft_board()
            board=apply_v92_injury_overlay(board,state)
else:
    players=pd.DataFrame()
    hist=pd.DataFrame()
    market=pd.DataFrame()
    board=_fast_local_draft_board()
    board=apply_v92_injury_overlay(board,state)

if board is None or board.empty:
    st.error("Fantasy Edge could not load the local player board.")
    st.stop()

# V6.45: replace rank-derived offensive estimates with published 2026 projections.
board,_v645_projection_matches,_v645_projection_error=_v645_apply_published_projections(
    board,ppr,teams,state["roster_slots"]
)
if _v645_projection_matches:
    st.sidebar.success(f"Published projections loaded: {_v645_projection_matches} players • unmatched offense marked No projection")
else:
    st.sidebar.caption("Published projection refresh unavailable; packaged board retained." +
                       (f" ({_v645_projection_error})" if _v645_projection_error else ""))

# V6.35 active NFL roster directory. Identity only.
# IMPORTANT: roster-only names are NOT merged into the ranked Fantasy Edge board.
# This preserves every certified projection, VORP and market pick exactly as-is.
# The directory is used only to expand the Live Draft selection dropdown/export.
_active_roster_export=pd.DataFrame()
try:
    _directory_players = players if isinstance(players,dict) and players else sleeper_players()
    _active_roster_export=_v633_active_roster_directory(_directory_players)
    _active_roster_export=_v637_attach_directory_ranks(_active_roster_export)
    _ranked_dir=int(pd.to_numeric(_active_roster_export.get("external_ecr_rank"),errors="coerce").notna().sum())
    _pre_enrich_keys=set(board["player"].astype(str).map(norm))
    board=_v642_enrich_ranked_roster_players(board,_active_roster_export)
    _post_enrich_keys=set(board["player"].astype(str).map(norm))
    _ecr_added=len(_post_enrich_keys-_pre_enrich_keys)
    st.sidebar.success(f"Active roster synced: {len(_active_roster_export):,} NFL players • {_ranked_dir} with live consensus rank • {_ecr_added} model-enriched")
except Exception as _roster_sync_error:
    st.sidebar.caption("Active roster sync unavailable; certified local pool retained.")

# V6.21 UI master-pool repair: production_board.csv is authoritative for player
# identity. Merge any production player missing from the runtime board so external
# refreshes/caches cannot silently remove draftable players from Draft Mode.
try:
    _pb_master,_cfg_master=load_v9_production()
    _runtime_keys=set(board["player"].astype(str).map(norm))
    _missing_pb=_pb_master[~_pb_master["key"].astype(str).isin(_runtime_keys)].copy()
    if len(_missing_pb):
        _rows=[]
        for _,_r in _missing_pb.iterrows():
            _name=str(_r["Player"]); _pos=canonical_position(_r["Position"])
            _market=float(pd.to_numeric(pd.Series([_r.get("Market_pick",999)]),errors="coerce").fillna(999).iloc[0])
            _vorp=float(pd.to_numeric(pd.Series([_r.get("VORP",0)]),errors="coerce").fillna(0).iloc[0])
            _draft=float(pd.to_numeric(pd.Series([_r.get("Draft_score",0)]),errors="coerce").fillna(0).iloc[0])
            _model=float(pd.to_numeric(pd.Series([_r.get("Model_rank",999)]),errors="coerce").fillna(999).iloc[0])
            # V6.22 projection repair: Draft_score is a ranking score, NOT fantasy
            # points. Reconstruct a PPG-scale projection from the runtime position
            # replacement level + certified VORP. This keeps restored players on
            # the same scale as native players.
            _pos_runtime=board[board["position"].astype(str).eq(_pos)].copy()
            if len(_pos_runtime) and "projection" in _pos_runtime.columns and "vorp" in _pos_runtime.columns:
                _repl_series=(pd.to_numeric(_pos_runtime["projection"],errors="coerce")
                              -pd.to_numeric(_pos_runtime["vorp"],errors="coerce")).replace([np.inf,-np.inf],np.nan).dropna()
                _replacement=float(_repl_series.median()) if len(_repl_series) else np.nan
            else:
                _replacement=np.nan
            _fallback_repl={"QB":16.0,"RB":8.2,"WR":7.6,"TE":7.8,"K":7.0,"DL":6.2,"DB":5.9}
            if not np.isfinite(_replacement) or _replacement<0 or _replacement>30:
                _replacement=float(_fallback_repl.get(_pos,7.5))
            _projection=float(_replacement+_vorp)

            _rows.append({
                "id":"production:"+norm(_name),"player":_name,"key":norm(_name),
                "position":_pos,"raw_position":_pos,"team":"NFL",
                "projection":_projection,"vorp":_vorp,"replacement_ppg":_replacement,
                "draft_score":_draft,
                "model_rank":_model,"consensus_rank":_market,"market_pick":_market,
                "confidence":0.80,"injury":"","injury_penalty":0.0,
                "v9_market_pick":_market,"v9_vorp":_vorp,
                "v9_draft_score":_draft,"v9_model_rank":_model,
                "v9_base_live_score":float(_r.get("Base_live_score",_draft)),
            })
        board=pd.concat([board,pd.DataFrame(_rows)],ignore_index=True,sort=False)
    board=board.drop_duplicates(subset=["player"],keep="first").reset_index(drop=True)
    # Projection sanity certification: normal fantasy PPG values should never
    # resemble 0-100 Draft_score values.
    _proj_check=pd.to_numeric(board.get("projection",pd.Series(dtype=float)),errors="coerce")
    _bad_proj=board[_proj_check>40]["player"].astype(str).tolist() if len(board) else []
    if _bad_proj:
        raise RuntimeError("Projection scale contamination detected: "+", ".join(_bad_proj[:12]))
except Exception as _pool_merge_error:
    st.sidebar.error("Production player-pool merge failed: "+str(_pool_merge_error))

# V6.59 rosterable-player repair. Ownership eligibility is intentionally broader
# than recommendation eligibility: these players must be assignable to a Yahoo
# roster even when a player-specific projection is unavailable. Published
# offensive projections are overlaid by the normal Razzball/FantasyPros pass
# below; IDPs continue through the IDP model rather than receiving invented pts.
_v659_players=[
    ("Ja'Kobi Lane","WR","BAL"),
    ("Derrick Brown","DL","CAR"),
    ("Byron Young","DL","LAR"),
    ("Deion Burks","WR","IND"),
    ("Malik Davis","RB","NFL"),
    ("Kaleb Johnson","RB","GB"),
    ("Kamari Lassiter","DB","HOU"),
    ("Cyrus Allen","WR","KC"),
    ("Jordan Mason","RB","MIN"),
    ("Trey Smack","K","GB"),
    ("Javon Bullard","DB","GB"),
]
_existing_keys=set(board["player"].astype(str).map(norm)) if len(board) else set()
_add=[]
for _name,_pos,_team in _v659_players:
    if norm(_name) in _existing_keys: continue
    _add.append({
        "player":_name,"position":_pos,"raw_position":_pos,"team":_team,
        "projection":np.nan,"vorp":np.nan,"draft_score":0.0,"model_rank":999.0,
        "consensus_rank":np.nan,"market_pick":np.nan,"key":norm(_name),
        "profile":"Rosterable player — projection pending","confidence":0.50,
        "projection_source":"Projection lookup pending","projection_available":False,
        "recommendation_pool":False,
    })
if _add:
    board=pd.concat([board,pd.DataFrame(_add)],ignore_index=True,sort=False)
    board=board.drop_duplicates(subset=["key"],keep="first").reset_index(drop=True)

# V6.46 authoritative final projection pass. The packaged/top-300/production
# universe is finalized FIRST; published projections are then overlaid onto that
# complete universe. This prevents a later pool merge from reintroducing players
# (such as J.K. Dobbins) with stale rank-derived projection/VORP values.
board,_v646_projection_matches,_v646_projection_error=_v645_apply_published_projections(
    board,ppr,teams,state["roster_slots"]
)
# V6.59 targeted published fallback for a newly rosterable player when the live
# bulk endpoint has not indexed him yet. FantasyPros 2026 PPR: 87.9 season pts.
_jkl=board["player"].astype(str).map(norm).eq(norm("Ja'Kobi Lane"))
if _jkl.any() and board.loc[_jkl,"projection"].isna().all() and abs(float(ppr)-1.0)<0.01:
    board.loc[_jkl,"projection"]=87.9/17.0
    board.loc[_jkl,"display_projection"]=87.9/17.0
    board.loc[_jkl,"projection_available"]=True
    board.loc[_jkl,"projection_source"]="FantasyPros 2026 PPR season projection (87.9 pts)"
    board.loc[_jkl,"profile"]="Published projection fallback"

if _v646_projection_matches:
    st.sidebar.success(f"Final projection pass: {_v646_projection_matches} published matches • VORP recalculated only from real projections")
elif _v646_projection_error:
    st.sidebar.caption("Final projection pass unavailable; complete packaged pool retained. ("+_v646_projection_error+")")

# Every Streamlit tab body executes, even when the tab is not selected.
# Guarantee the minimum board schema for ALL tabs before rendering any of them.
_board_schema_defaults={
    "player":"","position":"","raw_position":"","team":"NFL",
    "projection":0.0,"vorp":0.0,"draft_score":0.0,"model_rank":999.0,
    "consensus_rank":np.nan,"market_pick":np.nan,
    "profile":"Stable / neutral","confidence":0.50,
    "breakout":0.0,"decline":0.0,"progression":0.0,"regression":0.0,
    "waiver_score":0.0,"injury":"","injury_source":"Local",
    "injury_effective":"","injury_severity":0,"injury_penalty":0.0,
    "display_projection":0.0,"display_vorp":0.0,"display_model_rank":999.0,
}
for _col,_default in _board_schema_defaults.items():
    if _col not in board.columns:
        board[_col]=_default

# V6.53: NEVER erase recorded live-draft state just because a temporary player
# feed/board rebuild does not contain a name. Roster-only picks are legitimate.
# Streamlit requires every multiselect default to exist in its options. Build the
# option universe from BOTH the current board and the saved live-draft state so
# an older/roster-only recorded player can never crash League Setup.
state["my_team"]=list(dict.fromkeys(str(x).strip() for x in (state.get("my_team",[]) or []) if str(x).strip()))
state["taken"]=list(dict.fromkeys(str(x).strip() for x in (state.get("taken",[]) or []) if str(x).strip()))
_board_names=[str(x).strip() for x in board["player"].astype(str).tolist() if str(x).strip()]
all_names=list(dict.fromkeys(_board_names + state["my_team"] + state["taken"]))
state=_ensure_ownership_state(state,all_names)
state=_sync_legacy_from_ownership(state)




# ---------------- V6.78 shared precomputed live context ----------------
@st.cache_data(ttl=1800, show_spinner=False)
def _v730_build_matchup_lookup(board_df, season, week):
    """V7.30 fresh player->matchup lookup. New function name intentionally busts stale Streamlit cache."""
    matchup_map=_v677_week_matchups(season,week)
    allowed=_v677_matchup_allowed_table(season)

    records=[]
    if board_df is None or board_df.empty:
        return pd.DataFrame(columns=["player","_opponent","_matchup_grade","_matchup_adjustment","_matchup_source"])

    for _,row in board_df[["player","team","position","projection"]].iterrows():
        ctx=_v677_matchup_context(row,matchup_map,allowed)
        records.append({
            "player":row["player"],
            "_opponent":ctx["opponent"],
            "_matchup_grade":ctx["grade"],
            "_matchup_adjustment":ctx["adjustment"],
            "_matchup_source":ctx["source"],
        })
    return pd.DataFrame(records)

def _v678_enrich_board_once(board_df):
    """Attach matchup context once; downstream tabs only filter/sort."""
    if board_df is None or board_df.empty:
        return board_df, {"season":datetime.now().year,"week":1}

    nfl_state=_v677_nfl_state()
    season=int(nfl_state.get("season",datetime.now().year))
    week=int(nfl_state.get("week",1))

    lookup=_v730_build_matchup_lookup(
        board_df[["player","team","position","projection"]].copy(),
        season,
        week
    )
    out=board_df.copy()
    if len(lookup):
        out=out.merge(lookup,on="player",how="left")
    else:
        out["_opponent"]="Schedule unavailable"
        out["_matchup_grade"]="—"
        out["_matchup_adjustment"]=0.0
        out["_matchup_source"]="No matchup"

    out["_opponent"]=out["_opponent"].fillna("Schedule unavailable")
    # V7.30: legacy V7.28/V7.29 cached strings are never allowed to render.
    _legacy_bad=out["_opponent"].astype(str).str.upper().str.strip().isin(["BYE / TBD","BYE/TBD","TBD"])
    out.loc[_legacy_bad,"_opponent"]="Schedule unavailable"
    out["_matchup_grade"]=out["_matchup_grade"].fillna("—")
    out["_matchup_adjustment"]=pd.to_numeric(out["_matchup_adjustment"],errors="coerce").fillna(0.0)
    out["_matchup_source"]=out["_matchup_source"].fillna("No matchup")
    return out, {"season":season,"week":week}

# ---------------- V6.77 live opponent + matchup context ----------------
@st.cache_data(ttl=1800, show_spinner=False)
def _v677_nfl_state():
    """Current NFL season/week from Sleeper. Falls back safely if unavailable."""
    try:
        r=requests.get("https://api.sleeper.app/v1/state/nfl",timeout=6)
        r.raise_for_status()
        d=r.json() if isinstance(r.json(),dict) else {}
        return {
            "season":int(d.get("season") or datetime.now().year),
            "week":max(1,int(d.get("week") or d.get("leg") or 1))
        }
    except Exception:
        return {"season":datetime.now().year,"week":1}

@st.cache_data(ttl=1800, show_spinner=False)
def _v677_week_matchups(season, week):
    """Reliable NFL opponent map: nflverse schedule first, ESPN fallback.

    Metadata keys distinguish a true bye from a failed schedule lookup so the UI
    never labels a feed failure as BYE / TBD.
    """
    alias={
        "WSH":"WAS","JAC":"JAX","LVR":"LV","OAK":"LV","STL":"LAR",
        "SD":"LAC","SDG":"LAC","LA":"LAR","HOU":"HOU"
    }
    def norm_team(v):
        x=str(v or "").upper().strip()
        return alias.get(x,x)
    def finalize(out, source):
        teams={k for k in out if not str(k).startswith("__")}
        out["__schedule_loaded__"]=True
        out["__scheduled_teams__"]=sorted(teams)
        out["__source__"]=source
        return out

    # Primary: nflverse's maintained schedules release (same data family used
    # elsewhere in Fantasy Edge and updated throughout the season).
    try:
        url="https://github.com/nflverse/nflverse-data/releases/download/schedules/games.csv"
        raw=pd.read_csv(url,low_memory=False)
        x=raw.copy()
        if "season" in x.columns:
            x=x[pd.to_numeric(x["season"],errors="coerce").eq(int(season))]
        if "week" in x.columns:
            x=x[pd.to_numeric(x["week"],errors="coerce").eq(int(week))]
        type_col="game_type" if "game_type" in x.columns else ("season_type" if "season_type" in x.columns else None)
        if type_col:
            x=x[x[type_col].astype(str).str.upper().isin(["REG","2","REGULAR"])]
        out={}
        if {"home_team","away_team"}.issubset(x.columns):
            for _,g in x.iterrows():
                home=norm_team(g.get("home_team")); away=norm_team(g.get("away_team"))
                if home and away and home!="NAN" and away!="NAN":
                    out[home]={"opponent":away,"site":"HOME"}
                    out[away]={"opponent":home,"site":"AWAY"}
        if out:
            return finalize(out,"nflverse schedules")
    except Exception:
        pass

    # Fallback: ESPN public scoreboard.
    try:
        url=(
            "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
            f"?dates={int(season)}&seasontype=2&week={int(week)}"
        )
        r=requests.get(url,timeout=8,headers={"User-Agent":"Mozilla/5.0"})
        r.raise_for_status()
        data=r.json()
        out={}
        for ev in data.get("events",[]) or []:
            comps=ev.get("competitions",[]) or []
            if not comps: continue
            competitors=comps[0].get("competitors",[]) or []
            if len(competitors)<2: continue
            teams=[]
            for c in competitors:
                abbr=norm_team((c.get("team") or {}).get("abbreviation"))
                teams.append((abbr,str(c.get("homeAway") or "").lower()))
            if len(teams)>=2 and teams[0][0] and teams[1][0]:
                a,ah=teams[0]; b,bh=teams[1]
                out[a]={"opponent":b,"site":"HOME" if ah=="home" else "AWAY"}
                out[b]={"opponent":a,"site":"HOME" if bh=="home" else "AWAY"}
        if out:
            return finalize(out,"ESPN scoreboard")
    except Exception:
        pass

    # V7.30 emergency authoritative fallback for 2026 Week 1.
    # This prevents a temporary upstream feed failure from ever turning a known
    # published Week 1 game into a fake BYE/TBD. Pairings mirror NFL.com.
    if int(season)==2026 and int(week)==1:
        pairs=[
            ("NE","SEA"),("SF","LAR"),("CHI","CAR"),("TB","CIN"),
            ("NO","DET"),("BUF","HOU"),("BAL","IND"),("CLE","JAX"),
            ("ATL","PIT"),("NYJ","TEN"),("ARI","LAC"),("MIA","LV"),
            ("GB","MIN"),("WAS","PHI"),("DAL","NYG"),("DEN","KC"),
        ]
        # first team is away, second is home in the published Week 1 schedule
        out={}
        for away,home in pairs:
            out[away]={"opponent":home,"site":"AWAY"}
            out[home]={"opponent":away,"site":"HOME"}
        return finalize(out,"NFL.com 2026 Week 1 fallback")

    return {"__schedule_loaded__":False,"__scheduled_teams__":[],"__source__":"unavailable"}

@st.cache_data(ttl=21600, show_spinner=False)
def _v677_matchup_allowed_table(current_season):
    """Fantasy points allowed by defense/opponent and position.

    Current-season data is preferred once there is usable weekly data. Until then,
    the most recent completed season is the fallback. This keeps Week 1 useful
    without pretending an unplayed 2026 sample already exists.
    """
    frames=[]
    seasons=[]
    try:
        cs=int(current_season)
    except Exception:
        cs=datetime.now().year
    for yr in [cs, cs-1]:
        try:
            url=f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{yr}.csv"
            raw=pd.read_csv(url,low_memory=False)
            if raw is None or raw.empty or "opponent_team" not in raw.columns or "position" not in raw.columns:
                continue
            x=raw.copy()
            if "season_type" in x.columns:
                x=x[x["season_type"].astype(str).str.upper().eq("REG")].copy()
            x["position"]=x["position"].astype(str).map(canonical_position)
            x=x[x["position"].isin(["QB","RB","WR","TE","DL","DB"])].copy()
            if x.empty:
                continue

            # Offensive PPR fantasy points.
            if "fantasy_points_ppr" in x.columns:
                x["_fp_off"]=pd.to_numeric(x["fantasy_points_ppr"],errors="coerce").fillna(0.0)
            else:
                for c in ["passing_yards","passing_tds","interceptions","rushing_yards","rushing_tds",
                          "receptions","receiving_yards","receiving_tds"]:
                    if c not in x.columns: x[c]=0.0
                x["_fp_off"]=(
                    pd.to_numeric(x["passing_yards"],errors="coerce").fillna(0)/25
                    + pd.to_numeric(x["passing_tds"],errors="coerce").fillna(0)*4
                    - pd.to_numeric(x["interceptions"],errors="coerce").fillna(0)*2
                    + pd.to_numeric(x["rushing_yards"],errors="coerce").fillna(0)/10
                    + pd.to_numeric(x["rushing_tds"],errors="coerce").fillna(0)*6
                    + pd.to_numeric(x["receptions"],errors="coerce").fillna(0)
                    + pd.to_numeric(x["receiving_yards"],errors="coerce").fillna(0)/10
                    + pd.to_numeric(x["receiving_tds"],errors="coerce").fillna(0)*6
                )

            # Generic IDP points only for matchup strength. Fantasy Edge's own
            # projection/VORP remains authoritative for player value.
            for c in ["def_tackles_solo","def_tackles_with_assist","def_sacks",
                      "def_tackles_for_loss","def_interceptions","def_pass_defended",
                      "def_fumbles_forced","def_tds","def_safety"]:
                if c not in x.columns: x[c]=0.0
            x["_fp_idp"]=(
                pd.to_numeric(x["def_tackles_solo"],errors="coerce").fillna(0)*1.5
                + pd.to_numeric(x["def_tackles_with_assist"],errors="coerce").fillna(0)*0.75
                + pd.to_numeric(x["def_sacks"],errors="coerce").fillna(0)*4.0
                + pd.to_numeric(x["def_tackles_for_loss"],errors="coerce").fillna(0)*1.0
                + pd.to_numeric(x["def_interceptions"],errors="coerce").fillna(0)*4.0
                + pd.to_numeric(x["def_pass_defended"],errors="coerce").fillna(0)*1.5
                + pd.to_numeric(x["def_fumbles_forced"],errors="coerce").fillna(0)*2.0
                + pd.to_numeric(x["def_tds"],errors="coerce").fillna(0)*6.0
                + pd.to_numeric(x["def_safety"],errors="coerce").fillna(0)*2.0
            )
            x["_fp"]=np.where(x["position"].isin(["DL","DB"]),x["_fp_idp"],x["_fp_off"])
            x["opponent_team"]=x["opponent_team"].astype(str).str.upper()
            x["week"]=pd.to_numeric(x.get("week",1),errors="coerce").fillna(1).astype(int)

            # Sum all players in a position group for each defense/opponent in a week,
            # then average weekly points allowed.
            g=(x.groupby(["opponent_team","position","week"],as_index=False)["_fp"].sum()
                 .groupby(["opponent_team","position"],as_index=False)
                 .agg(allowed_ppg=("_fp","mean"),sample_weeks=("_fp","size")))
            g["season"]=yr
            frames.append(g)
            seasons.append(yr)
        except Exception:
            continue

    if not frames:
        return pd.DataFrame(columns=["opponent_team","position","allowed_ppg","sample_weeks","season","league_avg","matchup_index"])

    allg=pd.concat(frames,ignore_index=True)
    # Prefer current season where a defense/position has at least two completed weeks;
    # otherwise use prior-season baseline.
    rows=[]
    for (opp,pos),g in allg.groupby(["opponent_team","position"]):
        g=g.sort_values("season",ascending=False)
        cur=g[(g["season"].eq(cs)) & (g["sample_weeks"]>=2)]
        chosen=cur.iloc[0] if len(cur) else g.iloc[-1] if len(g) else None
        if chosen is not None:
            rows.append(chosen.to_dict())
    out=pd.DataFrame(rows)
    if out.empty:
        return out
    out["league_avg"]=out.groupby("position")["allowed_ppg"].transform("mean")
    out["matchup_index"]=np.where(
        out["league_avg"]>0,
        (out["allowed_ppg"]/out["league_avg"]-1.0),
        0.0
    )
    return out

def _v677_matchup_context(row, matchup_map, allowed_table):
    team=str(row.get("team","") or "").upper().strip()
    pos=str(row.get("position","") or "").upper().strip()
    info=matchup_map.get(team,{}) if isinstance(matchup_map,dict) else {}
    opp=str(info.get("opponent","") or "")
    site=str(info.get("site","") or "")
    if not opp:
        loaded=bool(matchup_map.get("__schedule_loaded__",False)) if isinstance(matchup_map,dict) else False
        scheduled=set(matchup_map.get("__scheduled_teams__",[]) or []) if isinstance(matchup_map,dict) else set()
        # A missing team is a BYE only when a real schedule was successfully loaded.
        label="BYE" if loaded and team and team not in scheduled else "Schedule unavailable"
        source="Confirmed bye" if label=="BYE" else "Schedule lookup unavailable"
        return {"opponent":label,"site":"","grade":"—","index":0.0,"adjustment":0.0,"source":source}
    idx=0.0
    source="Prior-season defense"
    if isinstance(allowed_table,pd.DataFrame) and len(allowed_table):
        hit=allowed_table[
            allowed_table["opponent_team"].astype(str).eq(opp)
            & allowed_table["position"].astype(str).eq(pos)
        ]
        if len(hit):
            rr=hit.iloc[0]
            idx=float(pd.to_numeric(pd.Series([rr.get("matchup_index",0)]),errors="coerce").fillna(0).iloc[0])
            source=f"{int(rr.get('season',0))} points allowed"
    # Positive index = opponent allows more fantasy points than league average.
    idx=max(-0.25,min(0.25,idx))
    proj=float(pd.to_numeric(pd.Series([row.get("projection",0)]),errors="coerce").fillna(0).iloc[0])
    adjustment=max(-1.50,min(1.50,proj*0.35*idx))
    if idx>=0.10: grade="🔥 GREAT"
    elif idx>=0.04: grade="🟢 GOOD"
    elif idx<=-0.10: grade="🔴 TOUGH"
    elif idx<=-0.04: grade="🟠 BELOW AVG"
    else: grade="⚪ NEUTRAL"
    return {
        "opponent":("@"+opp if site=="AWAY" else "vs "+opp),
        "site":site,
        "grade":grade,
        "index":idx,
        "adjustment":adjustment,
        "source":source
    }

# ---------------- V6.76 roster-aware lineup / transaction engine ----------------
def _v676_injury_multiplier(value, practice=""):
    s=_v677_normalize_injury_status(value)
    p=str(practice or "").upper()
    if s=="ACTIVE":
        if "DNP" in p or "DID NOT PARTICIPATE" in p:
            return 0.90
        if "LIMIT" in p:
            return 0.96
        return 1.0
    if s in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return 0.0
    if s=="DOUBTFUL":
        return 0.35
    if s=="QUESTIONABLE":
        return 0.82
    return 0.96

def _v726_previous_external_projection(player_name):
    """Return the most recent saved external weekly projection for this player, if available."""
    try:
        hist=globals().get("state",{}).get("recommendation_history",[]) or []
        key=_owner_key(player_name)
        snaps=[x for x in hist if isinstance(x,dict)]
        snaps=sorted(snaps,key=lambda x:(int(x.get("season",0) or 0),int(x.get("week",0) or 0),str(x.get("saved_at",""))),reverse=True)
        for snap in snaps:
            for call in snap.get("start_sit",[]) or []:
                if _owner_key(call.get("starter",""))!=key:
                    continue
                val=pd.to_numeric(pd.Series([call.get("external_projection",np.nan)]),errors="coerce").iloc[0]
                if pd.notna(val) and float(val)>0:
                    return float(val)
    except Exception:
        pass
    return None


def _v726_market_signal(row):
    """Small market-context nudge for a pending practice ramp.

    This never creates a practice status.  A real movement signal uses the latest
    saved external projection when available.  Otherwise, current external-vs-FE
    agreement is used only as a weaker context signal.
    """
    if not _v719_external_projection_valid(row):
        return 0.0,"market signal unavailable"
    ext=_v682_num(row,"_external_week_projection",0)
    fe=_v682_num(row,"projection",0)
    prev=_v726_previous_external_projection(row.get("player",row.get("Player","")))
    if prev is not None and prev>0:
        delta=ext-prev
        pct=delta/max(prev,1.0)
        if delta>=1.5 or pct>=0.10:
            return 0.02,f"external market rising ({delta:+.1f})"
        if delta<=-1.5 or pct<=-0.10:
            return -0.02,f"external market falling ({delta:+.1f})"
        return 0.0,f"external market stable ({delta:+.1f})"
    if fe>0:
        gap=ext-fe
        pct=gap/max(fe,1.0)
        if gap>=2.0 or pct>=0.15:
            return 0.01,"external market above FE"
        if gap<=-2.0 or pct<=-0.15:
            return -0.01,"external market below FE"
        return 0.0,"external market agrees"
    return 0.0,"market signal unavailable"


def _v725_provisional_practice_ramp(row):
    """Transparent estimate while a matched practice report is pending.

    V7.26 blends prior practice trend, injury/body-part context, report recency,
    and a capped external-market signal.  Official Full/Limited/DNP remains
    authoritative and immediately bypasses this provisional path.
    """
    match=str(row.get("practice_match_status","") or "").lower().strip()
    current=str(row.get("practice_status","") or "").strip()
    if current or "participation not published" not in match:
        return None, ""

    prior=str(row.get("prior_practice_status","") or "").upper().strip()
    trend=str(row.get("practice_trend","") or "").strip()
    injury=str(row.get("injury_detail","") or "").upper().strip()
    pos=str(row.get("position","") or "").upper().strip()
    high_terms=("KNEE","HAMSTRING","QUAD","CALF","ANKLE","FOOT","ACHILLES","GROIN","HIP","HEAD","CONCUSSION")
    upper_terms=("SHOULDER","ELBOW","WRIST","HAND","RIB","CHEST","BACK")
    high=any(x in injury for x in high_terms)
    upper=any(x in injury for x in upper_terms)
    skill=pos in ("RB","WR","TE","DB","DL")

    if "FULL" in prior:
        mult=0.94; reason="prior Full"
    elif "LIMIT" in prior:
        mult=0.88; reason="prior Limited"
    elif "DNP" in prior or "DID NOT PARTICIPATE" in prior:
        mult=0.81; reason="prior DNP"
    else:
        mult=0.86; reason="no prior participation"

    if high and skill:
        mult-=0.02
    elif upper:
        mult-=0.01

    t=trend.upper()
    if "DNP → LIMITED" in t or "LIMITED → FULL" in t:
        mult+=0.02; trend_note="improving trend"
    elif "FULL → LIMITED" in t or "LIMITED → DNP" in t:
        mult-=0.03; trend_note="worsening trend"
    elif trend:
        trend_note=f"prior {trend}"
    else:
        trend_note="no published trend"

    # Fresh reports deserve slightly more caution; older lingering designations
    # are allowed to recover modestly while we wait for today's participation.
    recency_note="report recency unknown"
    raw_date=str(row.get("practice_updated",row.get("injury_updated","")) or "").strip()
    if raw_date:
        try:
            dt=pd.to_datetime(raw_date,errors="coerce",utc=True)
            if pd.notna(dt):
                age_days=max(0,int((pd.Timestamp.now(tz="UTC")-dt).days))
                if age_days<=1:
                    mult-=0.01; recency_note="fresh report"
                elif age_days>=4:
                    mult+=0.01; recency_note=f"lingering report ({age_days}d)"
                else:
                    recency_note=f"report {age_days}d old"
        except Exception:
            pass

    market_adj,market_note=_v726_market_signal(row)
    mult+=max(-0.02,min(0.02,market_adj))

    # Provisional estimates are intentionally capped below confirmed Full practice.
    mult=max(0.76,min(0.96,mult))
    injury_note=str(row.get("injury_detail","") or "").strip()
    basis=f"PENDING practice report • {reason} • {trend_note} • {recency_note} • {market_note}"
    if injury_note:
        basis+=f" • {injury_note}"
    return mult,basis


def _v722_return_ramp_context(row):
    """Return (multiplier, label, basis) for injury return management.

    V7.22 removes the blanket QUESTIONABLE=85% treatment. Pregame ramps are
    individualized using practice participation, injury/body-part context,
    recency, position, and—once available—verified current-season workload.
    Historical usage is context only and never restores the ramp by itself.
    """
    status=_v677_normalize_injury_status(row.get("injury_effective",row.get("injury","")))
    practice=str(row.get("practice_status","") or "").upper().strip()
    injury=str(row.get("injury_detail","") or "").upper().strip()
    pos=str(row.get("position","") or "").upper().strip()
    base=_v676_injury_multiplier(status,practice)

    if status in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return 0.0, "UNAVAILABLE (0%)", "Official unavailable/reserve designation"
    if status=="DOUBTFUL":
        return min(base,0.35), "DOUBTFUL RAMP (35%)", "Doubtful designation"

    # Injury-context severity nudges. These are intentionally modest: practice
    # and real usage remain the primary signals.
    lower_body_terms=("KNEE","HAMSTRING","QUAD","CALF","ANKLE","FOOT","ACHILLES","GROIN","HIP")
    upper_body_terms=("SHOULDER","ELBOW","WRIST","HAND","FINGER","RIB","CHEST","BACK")
    neuro_terms=("HEAD","CONCUSSION")
    high_risk=any(x in injury for x in lower_body_terms) or any(x in injury for x in neuro_terms)
    upper_risk=any(x in injury for x in upper_body_terms)
    skill_player=pos in ("RB","WR","TE","DB","DL")

    # Recent report age helps distinguish an old lingering tag from a fresh injury.
    age_days=None
    raw_date=str(row.get("injury_updated","") or "").strip()
    if raw_date:
        try:
            dt=pd.to_datetime(raw_date,errors="coerce",utc=True)
            if pd.notna(dt):
                age_days=int((pd.Timestamp.now(tz="UTC")-dt).days)
        except Exception:
            age_days=None
    very_recent=(age_days is not None and 0 <= age_days <= 7)

    # Current-season workload is the strongest evidence. It can restore a player
    # toward full role, but DNP/Limited practice can still cap the result.
    current_usage=str(row.get("_usage_recency","") or "").upper()=="CURRENT" and _v682_num(row,"_usage_games",0)>0
    if current_usage:
        opps=_v682_num(row,"_opps_last",0)
        snap_pct=_v682_num(row,"_snap_pct_last",0)
        benchmarks={"RB":14.0,"WR":7.0,"TE":5.0,"QB":1.0,"DL":1.0,"DB":1.0}
        bench=benchmarks.get(pos,7.0)
        ratio=(opps/bench) if bench>1 else 0.0
        if ratio>=0.95 or snap_pct>=0.80:
            usage_factor=1.00; usage_desc="full workload confirmed"
        elif ratio>=0.80 or snap_pct>=0.70:
            usage_factor=0.98; usage_desc="near-full workload confirmed"
        elif ratio>=0.60 or snap_pct>=0.55:
            usage_factor=0.94; usage_desc="role recovering"
        elif ratio>=0.40 or snap_pct>=0.40:
            usage_factor=0.89; usage_desc="partial workload"
        elif opps>0 or snap_pct>0:
            usage_factor=0.84; usage_desc="limited workload"
        else:
            usage_factor=0.82; usage_desc="current-season sample, minimal workload"

        if "DNP" in practice or "DID NOT PARTICIPATE" in practice:
            usage_factor=min(usage_factor,0.84)
            practice_desc="DNP cap"
        elif "LIMIT" in practice:
            usage_factor=min(usage_factor,0.92 if high_risk else 0.94)
            practice_desc="limited-practice cap"
        elif "FULL" in practice:
            usage_factor=max(usage_factor,0.98)
            practice_desc="full practice"
        else:
            practice_desc="no practice cap"

        mult=max(base,usage_factor) if status in ("ACTIVE","QUESTIONABLE") else base
        mult=max(0.0,min(1.0,mult))
        if mult>=0.985: label=f"USAGE RESTORED ({int(round(mult*100))}%)"
        elif mult>=0.90: label=f"ROLE RECOVERING ({int(round(mult*100))}%)"
        else: label=f"LIMITED ROLE ({int(round(mult*100))}%)"
        return mult,label,f"{usage_desc} • {practice_desc}"

    # Pregame dynamic ramp. Full / Limited / DNP each has a range, then injury
    # context chooses the point in that range instead of applying one blanket 85%.
    if status=="QUESTIONABLE":
        if "FULL" in practice:
            mult=0.98
            if high_risk and skill_player: mult-=0.01
            if very_recent: mult-=0.01
            mult=max(0.95,min(1.00,mult))
            basis="Full practice"
        elif "LIMIT" in practice:
            mult=0.91
            if high_risk and skill_player: mult-=0.03
            elif upper_risk: mult-=0.01
            if very_recent: mult-=0.01
            mult=max(0.85,min(0.92,mult))
            basis="Limited practice"
        elif "DNP" in practice or "DID NOT PARTICIPATE" in practice:
            mult=0.82
            if high_risk and skill_player: mult-=0.04
            elif upper_risk: mult-=0.02
            if very_recent: mult-=0.01
            mult=max(0.70,min(0.85,mult))
            basis="DNP / game-time risk"
        else:
            provisional,pbasis=_v725_provisional_practice_ramp(row)
            if provisional is not None:
                mult=provisional
                basis=pbasis
                return mult,f"PENDING PRACTICE — PROVISIONAL ({int(round(mult*100))}%)",basis
            mult=0.86
            if high_risk and skill_player: mult-=0.02
            if very_recent: mult-=0.01
            mult=max(0.82,min(0.88,mult))
            basis="Questionable — no practice detail"
        if injury:
            basis += f" • {str(row.get('injury_detail','')).strip()}"
        return mult,f"PREGAME RETURN RAMP ({int(round(mult*100))}%)",basis

    # ACTIVE players with a recent injury report receive only a mild temporary
    # ramp until current-season workload confirms the role.
    recent_marker=(age_days is not None and 0 <= age_days <= 35)
    if status=="ACTIVE" and recent_marker:
        if "DNP" in practice or "DID NOT PARTICIPATE" in practice:
            mult=0.90 if not high_risk else 0.86
            basis="Active but DNP on recent report"
        elif "LIMIT" in practice:
            mult=0.95 if not high_risk else 0.92
            basis="Active with limited practice"
        elif "FULL" in practice:
            mult=0.99 if not high_risk else 0.97
            basis="Active + full practice"
        else:
            mult=0.97 if not high_risk else 0.95
            basis="Active with recent injury marker"
        return min(base,mult),f"RETURN RAMP ({int(round(min(base,mult)*100))}%)",basis

    return base,f"FULL ROLE ({int(round(base*100))}%)","Healthy / no current return restriction"


def _v722_injury_return_multiplier(row):
    return _v722_return_ramp_context(row)[0]


def _v722_injury_return_label(row):
    return _v722_return_ramp_context(row)[1]


def _v722_injury_return_basis(row):
    return _v722_return_ramp_context(row)[2]

# Backward-compatible aliases so every V7.21 call site automatically uses V7.22.
def _v721_injury_return_multiplier(row):
    return _v722_injury_return_multiplier(row)


def _v721_injury_return_label(row):
    return _v722_injury_return_label(row)

def _v676_player_value(row):
    p=float(pd.to_numeric(pd.Series([row.get("projection",0)]),errors="coerce").fillna(0).iloc[0])
    v=float(pd.to_numeric(pd.Series([row.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
    matchup=float(pd.to_numeric(pd.Series([row.get("_matchup_adjustment",0)]),errors="coerce").fillna(0).iloc[0])
    role_adj=_v683_role_adjustment(row)
    base=p + max(-2.0,min(4.0,v))*0.08 + matchup + role_adj
    return max(0.0,base * _v721_injury_return_multiplier(row))

def _v676_optimize_lineup(roster_df):
    if roster_df is None or len(roster_df)==0:
        return pd.DataFrame(), pd.DataFrame(), 0.0
    r=roster_df.copy().reset_index(drop=True)
    r["_start_value"]=r.apply(_v676_player_value,axis=1)
    r["_idx"]=range(len(r))
    used=set()
    slots=[]

    def add_row(label,row):
        used.add(int(row["_idx"]))
        slots.append({
            "Slot":label,
            "_idx":int(row["_idx"]),
            "Player":row["player"],
            "Pos":row["position"],
            "Team":row.get("team",""),
            "Projected PPG":float(pd.to_numeric(pd.Series([row.get("projection",0)]),errors="coerce").fillna(0).iloc[0]),
            "Adjusted PPG":float(row["_start_value"]),
            "VORP":float(pd.to_numeric(pd.Series([row.get("vorp",0)]),errors="coerce").fillna(0).iloc[0]),
            "Status":_v677_status_icon(row.get("injury","")),
            "Practice":_v680_practice_risk(row.get("practice_status","")),
            "Injury":str(row.get("injury_detail","") or "—"),
            "Opponent":str(row.get("_opponent","—") or "—"),
            "Matchup":str(row.get("_matchup_grade","—") or "—"),
            "Matchup Adj":float(pd.to_numeric(pd.Series([row.get("_matchup_adjustment",0)]),errors="coerce").fillna(0).iloc[0]),
        })

    for pos,label,count in [("QB","QB",1),("RB","RB",2),("WR","WR",2),("TE","TE",1)]:
        avail=r[(r["position"].eq(pos)) & (~r["_idx"].isin(used))].sort_values("_start_value",ascending=False)
        for i,(_,row) in enumerate(avail.head(count).iterrows(),1):
            add_row(label if count==1 else f"{label}{i}",row)

    flex=r[r["position"].isin(["RB","WR","TE"]) & (~r["_idx"].isin(used))].sort_values("_start_value",ascending=False)
    for i,(_,row) in enumerate(flex.head(2).iterrows(),1):
        add_row(f"FLEX{i}",row)

    for pos,label in [("K","K"),("DL","DL"),("DB","DB")]:
        avail=r[(r["position"].eq(pos)) & (~r["_idx"].isin(used))].sort_values("_start_value",ascending=False)
        if len(avail):
            add_row(label,avail.iloc[0])

    starters=pd.DataFrame(slots)
    bench=r[~r["_idx"].isin(used)].copy().sort_values("_start_value",ascending=False)
    lineup_score=float(starters["Adjusted PPG"].sum()) if len(starters) else 0.0
    return starters,bench,lineup_score

def _v676_roster_score(roster_df):
    starters,bench,lineup=_v676_optimize_lineup(roster_df)
    depth=float(bench["_start_value"].head(6).sum())*0.18 if len(bench) else 0.0
    return lineup+depth

def _v678_scores_from_optimized(starters,bench,lineup):
    depth=float(bench["_start_value"].head(6).sum())*0.18 if len(bench) else 0.0
    return lineup+depth

def _v676_legal_drop(roster_df,drop_row,add_row):
    counts=roster_df["position"].value_counts().to_dict()
    dp=str(drop_row.get("position",""))
    ap=str(add_row.get("position",""))
    counts[dp]=counts.get(dp,0)-1
    counts[ap]=counts.get(ap,0)+1
    for p,floor in {"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DL":1,"DB":1}.items():
        if counts.get(p,0)<floor:
            return False
    return True

def _v676_move_label(net_roster,net_lineup,add_row):
    add_v=float(pd.to_numeric(pd.Series([add_row.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
    if net_roster>=2.5 or net_lineup>=1.5:
        return "🔥 CLAIM"
    if net_roster>=1.0 or net_lineup>=0.65:
        return "⬆️ ADD"
    if net_roster>=0.25 or (net_lineup>0 and add_v>0):
        return "👀 WATCH"
    if net_roster>-0.35 and add_v>0:
        return "🧳 STASH"
    return "⛔ PASS"

def _v676_reason(net_lineup,net_roster,add_row,drop_row):
    parts=[]
    parts.append("improves starting lineup" if net_lineup>=1.0 else "small lineup gain" if net_lineup>0.05 else "mostly depth")
    av=float(pd.to_numeric(pd.Series([add_row.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
    dv=float(pd.to_numeric(pd.Series([drop_row.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
    if av-dv>=1.5:
        parts.append("clear VORP upgrade")
    if _v676_injury_multiplier(drop_row.get("injury","")) < _v676_injury_multiplier(add_row.get("injury","")):
        parts.append("health upgrade")
    return " • ".join(parts)




# ---------------- V6.83 role + opportunity intelligence ----------------
@st.cache_data(ttl=21600, show_spinner=False)
def _v683_weekly_usage_table_current(season):
    """Current-season role/opportunity trends from nflverse weekly player stats."""
    try:
        yr=int(season)
    except Exception:
        yr=datetime.now().year
    try:
        url=f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{yr}.csv"
        x=pd.read_csv(url,low_memory=False)
        if x is None or x.empty or "week" not in x.columns:
            return pd.DataFrame()
        if "season_type" in x.columns:
            x=x[x["season_type"].astype(str).str.upper().eq("REG")].copy()

        name_col=next((c for c in ["player_display_name","player_name","display_name","full_name","player"] if c in x.columns),None)
        if not name_col:
            return pd.DataFrame()

        if "position" not in x.columns: x["position"]=""
        if "recent_team" not in x.columns: x["recent_team"]=x["team"] if "team" in x.columns else ""
        x["position"]=x["position"].astype(str).map(canonical_position)
        x["week"]=pd.to_numeric(x["week"],errors="coerce")
        x=x[x["week"].notna()].copy()
        if x.empty:
            return pd.DataFrame()

        def n(c):
            return pd.to_numeric(x[c],errors="coerce").fillna(0.0) if c in x.columns else pd.Series(0.0,index=x.index)

        x["_carries"]=n("carries")
        x["_targets"]=n("targets")
        x["_receptions"]=n("receptions")
        x["_touches"]=x["_carries"]+x["_receptions"]
        x["_opportunities"]=x["_carries"]+x["_targets"]

        snap_col=next((c for c in ["offense_snaps","offensive_snaps","snap_count","snaps"] if c in x.columns),None)
        snap_pct_col=next((c for c in ["offense_pct","offensive_snap_pct","snap_pct","snap_percentage"] if c in x.columns),None)
        route_col=next((c for c in ["routes_run","routes","route_count"] if c in x.columns),None)
        route_pct_col=next((c for c in ["route_participation","route_pct","route_percentage"] if c in x.columns),None)
        rz_tgt_col=next((c for c in ["red_zone_targets","rz_targets","targets_inside_20"] if c in x.columns),None)
        rz_car_col=next((c for c in ["red_zone_carries","rz_carries","carries_inside_20"] if c in x.columns),None)

        x["_snaps"]=pd.to_numeric(x[snap_col],errors="coerce").fillna(0.0) if snap_col else 0.0
        x["_snap_pct"]=pd.to_numeric(x[snap_pct_col],errors="coerce").fillna(0.0) if snap_pct_col else 0.0
        x["_routes"]=pd.to_numeric(x[route_col],errors="coerce").fillna(0.0) if route_col else 0.0
        x["_route_pct"]=pd.to_numeric(x[route_pct_col],errors="coerce").fillna(0.0) if route_pct_col else 0.0
        x["_rz_targets"]=pd.to_numeric(x[rz_tgt_col],errors="coerce").fillna(0.0) if rz_tgt_col else 0.0
        x["_rz_carries"]=pd.to_numeric(x[rz_car_col],errors="coerce").fillna(0.0) if rz_car_col else 0.0
        x["_fantasy_points"]=n("fantasy_points_ppr")

        # Explanatory decision-layer score; does not rewrite core projections/VORP.
        x["_role_score"]=(
            x["_opportunities"]
            + x["_rz_targets"]*1.8
            + x["_rz_carries"]*1.4
            + x["_routes"]*0.05
            + x["_snaps"]*0.02
        )

        rows=[]
        for name,g in x.groupby(name_col,dropna=True):
            g=g.sort_values("week").copy()
            if g.empty: continue
            latest=g.tail(2)
            prior=g.iloc[-4:-2] if len(g)>=3 else g.iloc[0:0]
            recent_role=float(latest["_role_score"].mean()) if len(latest) else 0.0
            prior_role=float(prior["_role_score"].mean()) if len(prior) else recent_role
            delta=recent_role-prior_role

            if len(prior)==0:
                trend="NEW / MONITOR"
            elif delta>=3.0 or (prior_role>0 and delta/prior_role>=0.22):
                trend="↑ ROLE RISING"
            elif delta<=-3.0 or (prior_role>0 and delta/prior_role<=-0.22):
                trend="↓ ROLE FALLING"
            else:
                trend="→ STABLE"

            last=g.iloc[-1]
            rows.append({
                "player":str(name).strip(),
                "_usage_team":str(last.get("recent_team","") or "").upper(),
                "_usage_position":str(last.get("position","") or ""),
                "_usage_week":int(last.get("week",0) or 0),
                "_carries_last":round(float(last.get("_carries",0)),1),
                "_targets_last":round(float(last.get("_targets",0)),1),
                "_touches_last":round(float(last.get("_touches",0)),1),
                "_opps_last":round(float(last.get("_opportunities",0)),1),
                "_snaps_last":round(float(last.get("_snaps",0)),1),
                "_snap_pct_last":round(float(last.get("_snap_pct",0)),3),
                "_routes_last":round(float(last.get("_routes",0)),1),
                "_route_pct_last":round(float(last.get("_route_pct",0)),3),
                "_rz_opp_last":round(float(last.get("_rz_targets",0)+last.get("_rz_carries",0)),1),
                "_role_score_recent":round(recent_role,2),
                "_role_score_prior":round(prior_role,2),
                "_role_delta":round(delta,2),
                "_role_trend":trend,
                "_recent_ppg3":round(float(g.tail(3)["_fantasy_points"].mean()),2),
                "_season_ppg_actual":round(float(g["_fantasy_points"].mean()),2),
                "_usage_games":int(len(g)),
                "_usage_source":"nflverse weekly stats"
            })
        return pd.DataFrame(rows)
    except Exception as e:
        pass  # cached loaders must not mutate session_state
        return pd.DataFrame()

def _v683_weekly_usage_table(season):
    """V7.07 usage loader: current season first, prior-season baseline only if current feed is unavailable.

    Historical fallback is diagnostic/context only and is never allowed to create a positive
    role adjustment by itself.
    """
    try:
        yr=int(season)
    except Exception:
        yr=datetime.now().year
    cur=_v683_weekly_usage_table_current(yr)
    if isinstance(cur,pd.DataFrame) and not cur.empty:
        cur=cur.copy(); cur["_usage_recency"]="CURRENT"
        return cur
    prev=_v683_weekly_usage_table_current(yr-1)
    if isinstance(prev,pd.DataFrame) and not prev.empty:
        prev=prev.copy()
        prev["_usage_recency"]="PRIOR_SEASON"
        prev["_usage_source"]=f"{yr-1} historical usage fallback"
        prev["_role_trend"]="HISTORICAL ROLE BASELINE"
        return prev
    return pd.DataFrame()

def _v743_role_confidence(row):
    """Evidence-weighted role confidence.

    Observed current-season usage is strongest. Before a player has logged a weekly-stat
    row, live team identity + an external weekly projection + market/model information can
    establish *inferred* role confidence. Inference is diagnostic/ranking context only; it
    never masquerades as observed snaps/touches and never creates a positive role adjustment.
    """
    rec=str(row.get("_usage_recency","") or "").upper()
    games=_v682_num(row,"_usage_games",0)
    if rec=="CURRENT" and games>0:
        conf=min(100.0,78.0+min(18.0,games*6.0))
        return round(conf,1),"OBSERVED GAME USAGE"
    score=0.0; signals=[]
    # V7.44: confidence is evidence quality, not fabricated usage. Team identity establishes
    # that the player has a current NFL context; a matched weekly projection is the strongest
    # pregame role signal. Market/model/FE information adds corroboration.
    if _v682_num(row,"_live_team_verified",0)>0:
        score+=30; signals.append("live team")
    ext=_v712_row_num(row,["_external_week_projection","external_projection"],0.0)
    if ext>0:
        score+=38; signals.append("weekly projection")
    market=_v712_row_num(row,["market_pick","Market_pick","market_rank","Market Rank","adp","ADP"],999.0)
    if market<=300:
        score+=16 if market<=120 else (12 if market<=240 else 8); signals.append("market")
    model=_v712_row_num(row,["model_rank","Model_rank","Model Rank","rank","Rank"],999.0)
    if model<=300:
        score+=12 if model<=120 else (9 if model<=240 else 6); signals.append("model")
    proj=max(0.0,_v712_row_num(row,["projection","Projection"],0.0))
    if proj>0:
        score+=8; signals.append("FE projection")
    if rec=="PRIOR_SEASON" and games>0:
        score+=4; signals.append("historical context")
    score=max(0.0,min(94.0,score))
    tier="HIGH" if score>=80 else ("USABLE" if score>=60 else ("WATCH" if score>=45 else "LOW"))
    label=(f"{tier} INFERRED — "+", ".join(signals[:3])) if signals else "LOW — no role evidence"
    return round(score,1),label

def _v683_role_adjustment(row):
    if str(row.get("_usage_recency","CURRENT") or "CURRENT").upper()!="CURRENT":
        return 0.0
    trend=str(row.get("_role_trend","") or "")
    try: delta=float(row.get("_role_delta",0) or 0)
    except Exception: delta=0.0
    try: opps=float(row.get("_opps_last",0) or 0)
    except Exception: opps=0.0
    adj=0.0
    if "RISING" in trend:
        adj += min(0.85,0.20+max(0,delta)*0.08)
    elif "FALLING" in trend:
        adj -= min(0.85,0.20+abs(min(0,delta))*0.08)
    if opps>=18: adj+=0.20
    elif opps>=12: adj+=0.10
    return max(-1.0,min(1.0,adj))

def _v683_enrich_role(board_df,season):
    if board_df is None or board_df.empty:
        return board_df
    usage=_v683_weekly_usage_table(season)
    out=board_df.copy()
    defaults={
        "_role_trend":"NO LIVE ROLE DATA","_role_delta":0.0,"_opps_last":0.0,
        "_touches_last":0.0,"_targets_last":0.0,"_carries_last":0.0,
        "_recent_ppg3":0.0,"_season_ppg_actual":0.0,"_usage_games":0,
        "_usage_source":"Unavailable","_usage_recency":"UNAVAILABLE","_snaps_last":0.0,"_snap_pct_last":0.0,
        "_routes_last":0.0,"_route_pct_last":0.0,"_rz_opp_last":0.0,
        "_role_score_recent":0.0
    }
    if usage is None or usage.empty:
        for c,v in defaults.items(): out[c]=v
        _rc=out.apply(_v743_role_confidence,axis=1)
        out["_role_confidence"]=[x[0] for x in _rc]
        out["_role_confidence_source"]=[x[1] for x in _rc]
        return out

    usage=usage.copy()
    usage["_key"]=usage["player"].map(_owner_key)
    out["_v683_key"]=out["player"].map(_owner_key)
    usecols=[c for c in usage.columns if c!="player"]
    out=out.merge(usage[usecols],left_on="_v683_key",right_on="_key",how="left")
    out.drop(columns=[c for c in ["_key","_v683_key"] if c in out.columns],inplace=True,errors="ignore")

    for c,v in defaults.items():
        if c not in out.columns:
            out[c]=v
        elif isinstance(v,(int,float)):
            out[c]=pd.to_numeric(out[c],errors="coerce").fillna(v)
        else:
            out[c]=out[c].fillna(v)
    _rc=out.apply(_v743_role_confidence,axis=1)
    out["_role_confidence"]=[x[0] for x in _rc]
    out["_role_confidence_source"]=[x[1] for x in _rc]
    return out

def _v683_role_summary(row):
    pieces=[]
    trend=str(row.get("_role_trend","") or "")
    if trend and "NO " not in trend:
        pieces.append(trend)
    try: opps=float(row.get("_opps_last",0) or 0)
    except Exception: opps=0
    try: tgts=float(row.get("_targets_last",0) or 0)
    except Exception: tgts=0
    try: carr=float(row.get("_carries_last",0) or 0)
    except Exception: carr=0
    if opps>0: pieces.append(f"{int(round(opps))} opps")
    if tgts>0: pieces.append(f"{int(round(tgts))} tgt")
    if carr>0: pieces.append(f"{int(round(carr))} car")
    return " • ".join(pieces) if pieces else "No recent role sample"

def _v683_find_beneficiary(inj_row,board_df,state):
    """Inference based on same-team role/usage; not an official depth-chart designation."""
    team=str(inj_row.get("team","") or "").upper()
    pos=str(inj_row.get("position","") or "")
    if not team or board_df is None or board_df.empty:
        return "—"
    peers=board_df[
        board_df["team"].astype(str).str.upper().eq(team)
        & ~board_df["player"].map(_owner_key).eq(_owner_key(inj_row.get("player","")))
    ].copy()
    if peers.empty: return "—"
    allowed={"RB":["RB"],"WR":["WR","TE"],"TE":["TE","WR"],"QB":["QB"],"DL":["DL"],"DB":["DB"]}.get(pos,[pos])
    peers=peers[peers["position"].isin(allowed)].copy()
    if peers.empty: return "—"

    peers["_benefit_score"]=(
        pd.to_numeric(peers.get("_role_score_recent",0),errors="coerce").fillna(0)
        + pd.to_numeric(peers.get("_role_delta",0),errors="coerce").fillna(0).clip(lower=0)*0.8
        + pd.to_numeric(peers.get("projection",0),errors="coerce").fillna(0).clip(lower=0)*0.15
    )
    best=peers.sort_values("_benefit_score",ascending=False).iloc[0]
    owner=_player_owner(state,best["player"])
    own_label="FA" if owner=="FA" else ("MY TEAM" if owner=="1" else "ROSTERED")
    trend=str(best.get("_role_trend","") or "")
    return f"{best['player']} ({own_label})" + (f" • {trend}" if trend and "NO " not in trend else "")

def _v683_data_health(board_df,season,week):
    total=max(1,len(board_df))
    injury=int(board_df.get("injury_source",pd.Series("",index=board_df.index)).fillna("").astype(str).str.strip().ne("").sum())
    matchup_src=board_df.get("_matchup_source",pd.Series("",index=board_df.index)).fillna("").astype(str)
    matchup=int((~matchup_src.str.contains("No matchup",case=False,na=False)).sum())
    role=int((pd.to_numeric(board_df.get("_role_confidence",pd.Series(0,index=board_df.index)),errors="coerce").fillna(0)>=60).sum())
    return {
        "season":season,"week":week,"players":len(board_df),
        "injury_coverage":round(injury/total*100),
        "matchup_coverage":round(matchup/total*100),
        "role_coverage":round(role/total*100),
        "injury_error":st.session_state.get("_v680_injury_watch_error") or st.session_state.get("_v681_sleeper_injury_error") or "",
        "matchup_error":st.session_state.get("_v677_schedule_error") or "",
        "role_error":st.session_state.get("_v683_usage_error") or ""
    }


# ---------------- V7.39 Temporary Opportunity / Injury Replacement Boost ----------------
def _v739_temporary_opportunity(add_row, roster_df, news_risk=None):
    """Return a temporary weekly opportunity boost for a direct injury replacement.

    This does not rewrite the player's base projection or ROS model. It is a waiver-week
    context layer: a free agent on the same NFL team and at the same fantasy position as
    an unavailable rostered player gets credit for the role that may temporarily open.
    The boost automatically disappears when the rostered teammate is playable again.
    """
    bad_weight={
        "OUT":1.00,"IR":1.00,"PUP":1.00,"NFI":1.00,"SUSPENDED":0.90,
        "DOUBTFUL":0.88,
    }
    news_risk=news_risk or {}
    if roster_df is None or not isinstance(roster_df,pd.DataFrame) or roster_df.empty:
        return 0.0,"","",0.0
    team=str(add_row.get("team","") or "").upper().strip()
    pos=str(add_row.get("position","") or "").upper().strip()
    if not team or not pos:
        return 0.0,"","",0.0
    same=roster_df[(roster_df["team"].astype(str).str.upper().eq(team)) &
                   (roster_df["position"].astype(str).str.upper().eq(pos))].copy()
    if same.empty:
        return 0.0,"","",0.0

    best=None
    for _,r in same.iterrows():
        stx=_v677_normalize_injury_status(r.get("injury_effective",r.get("injury","")))
        wt=bad_weight.get(stx,0.0)
        # Breaking news can justify preparation before the official designation changes.
        # It is deliberately a smaller, provisional weight and never rewrites status.
        if wt<=0 and str(news_risk.get(_owner_key(r.get("player","")),"")).upper()=="HIGH":
            wt=0.72
            stx="HIGH NEWS RISK (official status unchanged)"
        if wt<=0:
            continue
        # The unavailable player's own weekly/ROS value is evidence of how meaningful
        # the vacated role is, while the add's baseline projection keeps low-role backups
        # from receiving an unrealistic full-starter bump.
        source_week=max(0.0,_v676_player_value(r))
        add_proj=max(0.0,_v682_num(add_row,"projection",0))
        add_role=max(0.0,_v683_role_adjustment(add_row))
        raw=(1.75 + min(1.35,source_week*0.075) + min(0.55,add_proj*0.055) + min(0.35,add_role*0.25))*wt
        boost=max(0.0,min(4.25,raw))
        confidence=max(0.55,min(0.96,0.58+0.34*wt + min(0.04,add_proj/200.0)))
        cand=(boost,str(r.get("player","")),stx,confidence)
        if best is None or cand[0]>best[0]:
            best=cand
    if best is None:
        return 0.0,"","",0.0
    boost,source,status,confidence=best
    reason=f"{source} {status} → same-team {pos} role opportunity"
    return round(boost,2),reason,source,round(confidence,2)

def _v739_apply_temporary_opportunity(add_row, roster_df, news_risk=None):
    """Copy a candidate row with only its *weekly* projection temporarily adjusted."""
    row=add_row.copy()
    boost,reason,source,confidence=_v739_temporary_opportunity(row,roster_df,news_risk)
    base=max(0.0,_v682_num(row,"projection",0))
    row["_v739_base_projection"]=base
    row["_v739_opportunity_boost"]=boost
    row["_v739_opportunity_reason"]=reason
    row["_v739_opportunity_source"]=source
    row["_v739_opportunity_confidence"]=confidence
    if boost>0:
        row["projection"]=round(base+boost,2)
    return row


# ---------------- V7.41 Contextual Waiver Decision Engine ----------------
def _v741_contextual_waiver_score(row, best_effective_ppg=0.0):
    """Tie-break close waiver candidates using roster objective and role certainty.

    Core projections/VORP remain untouched. This score only ranks already-legal waiver
    transactions after the existing protection/emergency gates have run. A direct same-team
    injury replacement receives extra credit only when its effective weekly projection is
    close to the best candidate, so context cannot rescue a clearly inferior player.
    """
    eff=max(0.0,_v682_num(row,"Effective Add PPG",0))
    opp=max(0.0,_v682_num(row,"Opportunity Boost",0))
    conf=max(0.0,min(1.0,_v682_num(row,"Opportunity Confidence",0)))
    evidence=max(0.0,_v682_num(row,"Evidence",0))
    net_week=_v682_num(row,"Net Week",0)
    net_ros=_v682_num(row,"Net ROS",0)
    emergency=bool(row.get("Emergency Coverage",False))
    gap=max(0.0,float(best_effective_ppg or 0)-eff)

    # Projection remains the anchor. Context matters most inside a 1.5-point cluster.
    score=42.0 + min(30.0,eff*3.0)
    score += max(-3.0,min(7.0,net_week*1.6))
    score += max(-3.0,min(5.0,net_ros*0.35))
    score += min(4.0,evidence*1.25)

    fit="STANDARD"
    reasons=[]
    if emergency:
        reasons.append("required-position coverage")
    if opp>0 and conf>0:
        # Full role-certainty bonus only applies to close choices. It fades to zero by
        # a 1.5 projected-point deficit and automatically disappears with the opportunity.
        close_factor=max(0.0,min(1.0,(1.5-gap)/1.5))
        role_bonus=(6.0 + min(5.0,opp*1.8))*conf*close_factor
        score += role_bonus
        if gap<=1.5:
            fit="BEST CONTEXT FIT" if close_factor>=0.45 else "STRONG CONTEXT FIT"
            reasons.append("direct injury-replacement role")
            reasons.append(f"role confidence {conf:.0%}")
            if gap>0:
                reasons.append(f"only {gap:.2f} PPG behind top raw option")
        else:
            reasons.append("temporary role boost, but raw gap is too large")
    elif emergency:
        fit="WEEKLY COVERAGE"

    score=max(0.0,min(100.0,score))
    if not reasons:
        reasons.append("projection-led ranking")
    return round(score,1),fit," • ".join(reasons)

# ---------------- V7.42 Unified News / Contingency Context ----------------
_V742_NEWS_INJURY_TERMS=("injury","injured","surgery","procedure","meniscus","sprain","strain","hamstring","knee","ankle","shoulder","concussion","miss","out","week-to-week","questionable","doubtful")
_V742_NEWS_HIGH_TERMS=("surgery","procedure","expected to miss","will miss","miss a game","miss 1","miss 2","meniscus","placed on ir","injured reserve","out indefinitely")
_V742_TRUSTED_NEWS=("nfl.com","espn","associated press","ap news","reuters","the athletic","sports illustrated","yahoo sports","cbs sports","nbc sports","fox sports")

def _v742_classify_news(title,description=""):
    """Classify a recent headline without confusing a denial with an absence report."""
    text=re.sub(r"\s+"," ",f"{title} {description}").lower().strip()
    if not any(k in text for k in _V742_NEWS_INJURY_TERMS):
        return "NONE",0.0
    negated=bool(re.search(r"\b(?:not|won't|will not|isn't|is not|unlikely to)\b.{0,35}\b(?:miss|out|surgery|procedure)\b",text))
    high=(not negated) and any(k in text for k in _V742_NEWS_HIGH_TERMS)
    source=(str(title).rsplit(" - ",1)[-1] if " - " in str(title) else "").lower()
    trusted=any(k in source for k in _V742_TRUSTED_NEWS)
    if high:
        return "HIGH",(0.90 if trusted else 0.76)
    return "ELEVATED",(0.72 if trusted else 0.58)

@st.cache_data(ttl=900,show_spinner=False)
def _v742_google_news_player(player):
    """Recent news only; never changes the official injury designation."""
    try:
        q=quote_plus(f'"{player}" (injury OR surgery OR miss OR questionable OR knee OR ankle OR hamstring OR concussion) when:2d')
        url=f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        r=requests.get(url,timeout=5,headers={"User-Agent":f"Mozilla/5.0 FantasyEdge/{APP_VERSION}"})
        r.raise_for_status(); root=ET.fromstring(r.content)
        rows=[]; now=datetime.now(timezone.utc)
        for item in root.findall('.//item')[:12]:
            title=(item.findtext('title') or '').strip()
            desc=re.sub('<[^>]+>',' ',item.findtext('description') or '')
            if norm(player) not in norm(title+' '+desc):
                continue
            published=item.findtext('pubDate') or ''
            try:
                age_hours=max(0.0,(now-parsedate_to_datetime(published).astimezone(timezone.utc)).total_seconds()/3600.0)
            except Exception:
                age_hours=999.0
            if age_hours>60.0:
                continue
            risk,confidence=_v742_classify_news(title,desc)
            if risk=="NONE":
                continue
            rows.append({"Player":player,"Headline":title,"Published":published,"URL":item.findtext('link') or '',"News Risk":risk,"News Confidence":round(confidence,2)})
        return rows[:3]
    except Exception:
        return []

@st.cache_data(ttl=900,show_spinner=False)
def _v742_news_watch(board_df,state_snapshot):
    """Fetch watched-player news concurrently and return one best signal per player."""
    my=board_df[board_df['player'].map(lambda n:_player_owner(state_snapshot,n)=='1')].copy()
    if my.empty:
        return pd.DataFrame()
    bad={"OUT","DOUBTFUL","IR","PUP","NFI","SUSPENDED"}
    active=my[~my.apply(lambda r:_v677_normalize_injury_status(r.get('injury_effective',r.get('injury',''))) in bad,axis=1)].copy()
    counts=active['position'].astype(str).value_counts().to_dict()
    watch=active[active['position'].astype(str).isin(['QB','TE','K','DL','DB']) & active['position'].astype(str).map(lambda p:counts.get(p,0)<=1)].copy()
    concern=my[my.apply(lambda r:_v677_normalize_injury_status(r.get('injury_effective',r.get('injury',''))) not in ('ACTIVE',''),axis=1)]
    watch=pd.concat([watch,concern],ignore_index=True).drop_duplicates('player').head(8)
    players=watch['player'].astype(str).tolist()
    found=[]
    if players:
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(6,len(players))) as pool:
            for result in pool.map(_v742_google_news_player,players):
                found.extend(result)
    for row in found:
        match=watch[watch['player'].map(_owner_key).eq(_owner_key(row['Player']))]
        if match.empty:
            continue
        src=match.iloc[0]; pos=str(src.get('position',''))
        row.update({"Pos":pos,"Official Status":_v677_normalize_injury_status(src.get('injury_effective',src.get('injury',''))),"Expected":"reported availability concern","Depth":int(counts.get(pos,0))})
    if not found:
        return pd.DataFrame()
    out=pd.DataFrame(found); out['_sev']=out['News Risk'].map({'HIGH':0,'ELEVATED':1}).fillna(9)
    return out.sort_values(['_sev','News Confidence','Player'],ascending=[True,False,True]).drop_duplicates('Player').drop(columns='_sev')

def _v742_news_risk_map(news_df):
    if news_df is None or not isinstance(news_df,pd.DataFrame) or news_df.empty:
        return {}
    return {_owner_key(r.get('Player','')):str(r.get('News Risk','')).upper() for _,r in news_df.iterrows()}

def _v742_transaction_score(row):
    """One add/drop utility score shared by recommendation surfaces."""
    context=_v682_num(row,"Decision Score",0)
    net_week=_v682_num(row,"Net Week",0)
    net_ros=_v682_num(row,"Net ROS",0)
    drop_cost=max(0.0,_v682_num(row,"Drop Cost",0))
    drop_rank=max(0.0,_v682_num(row,"Emergency Drop Rank",drop_cost))
    score=context + max(-7.0,min(10.0,net_week*2.0)) + max(-5.0,min(7.0,net_ros*0.30))
    score -= min(18.0,drop_cost*0.28)
    if bool(row.get("Emergency Coverage",False)):
        score += 8.0
        score -= min(10.0,drop_rank*0.10)
    return round(max(0.0,min(100.0,score)),1)

# ---------------- V6.82 weekly decision helpers ----------------
def _v682_num(row, key, default=0.0):
    try:
        return float(pd.to_numeric(pd.Series([row.get(key,default)]),errors="coerce").fillna(default).iloc[0])
    except Exception:
        return float(default)

def _v682_ros_value(row):
    """
    Rest-of-season value proxy using existing Fantasy Edge signals only.
    It intentionally does NOT change core projection/VORP scoring.
    """
    proj=max(0.0,_v682_num(row,"projection",0))
    vorp=_v682_num(row,"vorp",0)
    breakout=max(0.0,min(1.0,_v682_num(row,"breakout",0)))
    decline=max(0.0,min(1.0,_v682_num(row,"decline",0)))
    conf=max(0.0,min(1.0,_v682_num(row,"confidence",0.5)))
    trend=(breakout-decline)*1.10
    return max(0.0, proj + max(-3.0,min(5.0,vorp))*0.22 + trend + (conf-0.5)*0.40)

def _v682_drop_protection(row):
    # V7.09: reserve-list protection must not depend on the display injury column.
    # A stale local/manual status previously let verified IR/PUP assets (e.g. Tank Dell)
    # leak back into the waiver drop pool even while protected drops was OFF.
    player_key=_owner_key(row.get("player",row.get("Player","")))
    verified=_V679_VERIFIED_RESERVE.get(player_key,{}) if isinstance(_V679_VERIFIED_RESERVE,dict) else {}
    verified_status=_v677_normalize_injury_status(verified.get("status","")) if verified else "ACTIVE"
    effective_status=row.get("injury_effective",row.get("injury",""))
    status=verified_status if verified_status in ("IR","PUP","NFI","SUSPENDED") else _v677_normalize_injury_status(effective_status)

    # V7.10 hard invariant: a player on the verified reserve map is protected
    # unconditionally when protected drops are disabled.  V7.09 still applied
    # an upside/value test after resolving the verified status, which meant a
    # reserve player with suppressed IR projections could receive an empty
    # protection label and leak into _eligible_drops.
    if verified and verified_status in ("IR","PUP","NFI","SUSPENDED"):
        return "🔒 VERIFIED RESERVE HOLD"

    ros=_v682_ros_value(row)
    vorp=_v682_num(row,"vorp",0)
    proj=_v682_num(row,"projection",0)
    rank=_v682_num(row,"model_rank",999)
    ext=_v682_num(row,"_external_week_projection",0)
    if status in ("IR","PUP","NFI") and (vorp>0 or rank<=230 or ros>=max(4.0,proj) or ext>=4.0):
        return "🔒 HOLD / IR STASH"
    if vorp>=2.0 or rank<=70:
        return "🔒 CORE HOLD"
    if vorp>=0.75 or rank<=130:
        return "🛡️ PREFER HOLD"
    return ""


def _v745_drop_tier(row, starter_names=None):
    """Context-aware waiver protection tier.

    LOCKED is a true no-cut asset in normal waiver mode. PROTECTED is a valuable
    starter/elite bench asset. CONDITIONAL may be cut when the incoming move earns it,
    and DROPPABLE is ordinary bottom-of-roster churn. This deliberately separates the
    old display protection label from transaction eligibility.
    """
    starter_keys={_owner_key(x) for x in (starter_names or [])}
    name=str(row.get("player",row.get("Player","")) or "")
    key=_owner_key(name)
    prot=str(_v682_drop_protection(row) or "")
    cost=float(_v711_drop_asset_cost(row,starter_names))
    rank=_v712_row_num(row,["model_rank","Model Rank"],999.0)
    vorp=_v712_row_num(row,["vorp","VORP"],0.0)

    if "VERIFIED RESERVE" in prot and _v740_reserve_return_week(row)<=0:
        return "LOCKED"
    if key in starter_keys:
        return "PROTECTED"
    if cost>=45.0 or rank<=70 or vorp>=2.0:
        return "PROTECTED"
    if cost>=15.0 or prot:
        return "CONDITIONAL"
    return "DROPPABLE"

def _v745_contextual_drop_ok(row, starter_names=None):
    """Normal-mode candidate admission; final transaction guards still decide the move."""
    return _v745_drop_tier(row,starter_names) in ("CONDITIONAL","DROPPABLE")

def _v712_row_num(row, keys, default=0.0):
    """Read a numeric signal across legacy/runtime column spellings."""
    for key in keys:
        try:
            if key in row and pd.notna(row.get(key)):
                return float(row.get(key))
        except Exception:
            pass
    return float(default)


def _v711_drop_asset_cost(row, starter_names=None):
    """
    Opportunity-cost score for cutting a roster asset. Higher = harder to justify dropping.
    V7.14 makes this robust to legacy column casing and normalized player identity so the
    score is actually useful as a transaction veto instead of only a display metric.
    """
    starter_keys={_owner_key(x) for x in (starter_names or [])}
    name=str(row.get("player",row.get("Player","")) or "")
    name_key=_owner_key(name)
    pos=str(row.get("position",row.get("Position",row.get("Pos",""))) or "").upper()
    cost=0.0
    if name_key in starter_keys:
        cost+=35.0

    market=_v712_row_num(row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)
    if market<=50: cost+=32.0
    elif market<=90: cost+=27.0
    elif market<=140: cost+=21.0
    elif market<=200: cost+=13.0
    elif market<=240: cost+=6.0

    model_rank=_v712_row_num(row,["model_rank","Model_rank","Model Rank"],999.0)
    if model_rank<=60: cost+=16.0
    elif model_rank<=120: cost+=10.0
    elif model_rank<=180: cost+=5.0

    vorp=_v712_row_num(row,["vorp","VORP"],0.0)
    cost+=max(0.0,min(18.0,vorp*4.0))
    ros=_v682_ros_value(row)
    cost+=max(0.0,min(18.0,ros*0.95))
    proj=max(0.0,_v712_row_num(row,["projection","Projection","_external_week_projection","external_projection"],0.0))
    cost+=max(0.0,min(11.0,proj*0.50))

    # RB/WR carry FLEX value and are intentionally harder to throw away for luxury depth.
    if pos in ("RB","WR"):
        cost+=7.0
    elif pos in ("QB","TE","DL","DB"):
        cost+=2.0
    return round(max(0.0,min(100.0,cost)),1)


def _v712_add_asset_strength(row):
    """Comparable incoming-asset strength used only by the waiver transaction guard."""
    pos=str(row.get("position",row.get("Position",row.get("Pos",""))) or "").upper()
    strength=0.0
    market=_v712_row_num(row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)
    if market<=50: strength+=32.0
    elif market<=90: strength+=27.0
    elif market<=140: strength+=21.0
    elif market<=200: strength+=13.0
    elif market<=240: strength+=6.0
    model_rank=_v712_row_num(row,["model_rank","Model_rank","Model Rank"],999.0)
    if model_rank<=60: strength+=16.0
    elif model_rank<=120: strength+=10.0
    elif model_rank<=180: strength+=5.0
    vorp=_v712_row_num(row,["vorp","VORP"],0.0)
    strength+=max(0.0,min(18.0,vorp*4.0))
    ros=_v682_ros_value(row)
    strength+=max(0.0,min(18.0,ros*0.95))
    proj=max(0.0,_v712_row_num(row,["projection","Projection","_external_week_projection","external_projection"],0.0))
    strength+=max(0.0,min(11.0,proj*0.50))
    if pos in ("RB","WR"):
        strength+=7.0
    elif pos in ("QB","TE","DL","DB"):
        strength+=2.0
    return round(max(0.0,min(100.0,strength)),1)


def _v711_move_viable(add_row, drop_row, net_week, net_ros, need_label, starter_names=None):
    """V7.14 transaction veto: do not manufacture a waiver move when HOLD is better."""
    starter_keys={_owner_key(x) for x in (starter_names or [])}
    drop_name=str(drop_row.get("player",drop_row.get("Player","")) or "")
    drop_key=_owner_key(drop_name)
    add_pos=str(add_row.get("position",add_row.get("Position","")) or "").upper()
    need=str(need_label or "").lower()
    drop_cost=_v711_drop_asset_cost(drop_row,starter_names)
    add_strength=_v712_add_asset_strength(add_row)
    add_market=_v712_row_num(add_row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)
    drop_market=_v712_row_num(drop_row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)

    luxury=("covered" in need or "deep" in need or "already" in need)
    net_week=float(net_week)
    net_ros=float(net_ros)
    meaningful_week=net_week>=0.75
    clear_week=net_week>=1.25
    major_ros=net_ros>=2.75
    exceptional_ros=net_ros>=4.0

    # A covered/deep-position add is optional. If it does not materially improve the
    # starting lineup or create a huge ROS gain, HOLD is the recommendation.
    if luxury and not (clear_week or exceptional_ros):
        return False,"HOLD — covered position / no material gain",drop_cost

    # Never sacrifice an optimized starter without a clear payoff.
    if drop_key in starter_keys and not (clear_week or exceptional_ros):
        return False,"HOLD — starter asset cost too high",drop_cost

    # Stash-level gains must use a truly expendable drop. This is the hard constraint
    # V7.14 was missing: Drop Cost now vetoes the transaction rather than only lowering
    # its priority score after the move has already been admitted.
    if drop_cost>=25.0 and net_week<0.50 and net_ros<2.25:
        return False,"HOLD — no expendable drop",drop_cost

    # Asset-for-asset test. A waiver add may replace a valuable player only when the
    # incoming asset plus demonstrated lineup/ROS gain reasonably compensates for it.
    transaction_credit=max(0.0,net_week)*8.0 + max(0.0,net_ros)*4.0
    if drop_cost > add_strength + transaction_credit + 8.0:
        return False,"HOLD — incoming asset does not justify drop cost",drop_cost

    # Strong market assets get an additional guard against obviously weaker free agents.
    if drop_market<=160 and add_market>drop_market+35 and not (meaningful_week or major_ros):
        return False,"HOLD — market-value sacrifice",drop_cost

    return True,"",drop_cost

    return True,"",drop_cost



def _v714_final_transaction_ok(row):
    """V7.14 last-line waiver safety gate.

    This validator is intentionally *action based*, not projection based.  No noisy ROS
    estimate is allowed to turn a bench-level STASH/STREAMER/WATCH into permission to cut
    a meaningful roster asset.  Expensive drops are only legal for aggressive, clearly
    lineup-improving transactions.
    """
    call=str(row.get("Waiver Call","") or "").upper()
    need=str(row.get("Need Fit","") or "").lower()
    drop_cost=float(pd.to_numeric(pd.Series([row.get("Drop Cost",0)]),errors="coerce").fillna(0).iloc[0])
    net_week=float(pd.to_numeric(pd.Series([row.get("Net Week",0)]),errors="coerce").fillna(0).iloc[0])
    net_ros=float(pd.to_numeric(pd.Series([row.get("Net ROS",0)]),errors="coerce").fillna(0).iloc[0])
    add_pos=str(row.get("Pos","") or "").upper()

    low_commitment=any(tag in call for tag in ("STASH","STREAMER","WATCH","PASS"))
    aggressive=any(tag in call for tag in ("PRIORITY","ADD NOW"))
    luxury=any(tag in need for tag in ("covered","already","deep"))

    # HARD RULE: low-commitment recommendations can only use truly expendable assets.
    # No exception for noisy/large Net ROS values. This specifically prevents a Kamara-like
    # starter from being cut for a stash, streamer, watch, covered QB/TE/K, or IDP depth.
    if low_commitment and drop_cost >= 15.0:
        return False

    # Covered/deep-position adds have a lower acceptable opportunity cost because they are
    # optional roster luxuries rather than fixes to an active lineup hole.
    if luxury and drop_cost >= 10.0 and not (aggressive and net_week >= 1.50):
        return False

    # Bench QB/TE/K/IDP depth can never consume a meaningful RB/WR-style asset unless the
    # add is an aggressive claim that materially changes the starting lineup immediately.
    if add_pos in ("K","QB","TE","DL","DB") and drop_cost >= 12.0 and not (aggressive and net_week >= 1.75):
        return False

    # Any genuinely high-cost asset requires ADD NOW/PRIORITY plus a clear weekly payoff.
    if drop_cost >= 22.0 and not (aggressive and net_week >= 1.25):
        return False

    # Extreme asset cost requires an unmistakable lineup improvement; ROS-only estimates
    # are not sufficient because those are the signals that leaked bad moves in V7.12/V7.13.
    if drop_cost >= 30.0 and net_week < 2.0:
        return False

    return True



# ---------------- V7.37 Required Position Emergency Coverage ----------------
def _v748_required_position_need_state(roster_df, news_df=None):
    """Split required-position risk into HARD coverage holes and PREP-only watches.

    HARD means the roster truly has fewer playable options than the lineup requires.
    PREP means the roster still has a playable option, but a sole/last required starter
    is QUESTIONABLE or has credible breaking-news risk. PREP must never be promoted to
    REQUIRED COVERAGE until the player is actually unavailable.
    """
    req={"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DL":1,"DB":1}
    bad={"OUT","DOUBTFUL","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"}
    hard=set(); prep=set(); reasons={}
    if roster_df is None or roster_df.empty:
        return set(req),set(),{p:"no rostered option" for p in req}
    news_risk=_v742_news_risk_map(news_df)
    for pos,floor in req.items():
        sub=roster_df[roster_df["position"].astype(str).str.upper().eq(pos)]
        playable=[]; risky=[]
        for _,r in sub.iterrows():
            name=str(r.get("player","") or "")
            stx=_v677_normalize_injury_status(r.get("injury_effective",r.get("injury","")))
            risk=str(news_risk.get(_owner_key(name),"")).upper()
            if stx not in bad:
                playable.append(name)
                if stx=="QUESTIONABLE" or risk in ("HIGH","ELEVATED"):
                    risky.append((name,stx,risk))
        if len(playable)<floor:
            hard.add(pos)
            reasons[pos]=f"{len(playable)}/{floor} playable"
        elif len(playable)==floor and risky:
            prep.add(pos)
            who,stx,risk=risky[0]
            flags=[]
            if stx=="QUESTIONABLE": flags.append("QUESTIONABLE")
            if risk in ("HIGH","ELEVATED"): flags.append(f"news {risk}")
            reasons[pos]=f"{who}: "+" + ".join(flags)
    return hard,prep,reasons


def _v737_required_position_emergencies(roster_df, news_df=None):
    """Backward-compatible HARD coverage set only."""
    hard,_,_=_v748_required_position_need_state(roster_df,news_df)
    return hard


def _v748_immediate_coverage_candidate(row):
    """True only for a waiver player who can plausibly solve a current-week lineup hole."""
    bad={"OUT","DOUBTFUL","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"}
    stx=_v677_normalize_injury_status(row.get("injury_effective",row.get("injury","")))
    if stx in bad:
        return False
    # Required coverage is not the place for stale prospects, unsigned players, or
    # candidates without a current NFL identity/weekly role signal.
    if _v682_num(row,"_live_team_verified",0)<=0:
        return False
    if _v682_num(row,"_role_confidence",0)<45:
        return False
    proj=max(0.0,_v682_num(row,"projection",0))
    pos=str(row.get("position","") or "").upper()
    floors={"QB":5.0,"RB":2.0,"WR":2.0,"TE":2.0,"K":2.0,"DL":1.0,"DB":1.0}
    return proj>=floors.get(pos,1.0)

def _v740_reserve_return_week(drop_row):
    """Earliest eligible return week for verified reserve players when known.

    This is intentionally small and factual. Unknown reserve timelines remain protected;
    known multi-week absences can be considered only during a required-position emergency.
    """
    key=_owner_key(drop_row.get("player",drop_row.get("Player","")))
    fixed=_V679_VERIFIED_RESERVE.get(key,{}) if isinstance(_V679_VERIFIED_RESERVE,dict) else {}
    try:
        wk=int(fixed.get("earliest_week",0) or 0)
    except Exception:
        wk=0
    return wk

def _v737_emergency_drop_ok(drop_row, starter_names, emergency_pos):
    """Safety boundary for a required-position emergency add.

    V7.40 fixes the over-protection bug exposed by the Bowers contingency. A required
    lineup hole must evaluate the *whole bench*, including non-starting CORE HOLD labels
    that can be stale and verified reserve stashes with a known multi-week absence.
    Starters, the injured player being covered, unknown reserve stashes and extreme-value
    assets remain hard protected.
    """
    prot=str(_v682_drop_protection(drop_row) or "")
    pos=str(drop_row.get("position",drop_row.get("Position","")) or "").upper()
    name=str(drop_row.get("player",drop_row.get("Player","")) or "")
    cost=_v711_drop_asset_cost(drop_row,starter_names)
    starter_keys={_owner_key(x) for x in (starter_names or [])}

    # Never solve a TE contingency by cutting the injured TE being covered.
    if pos==str(emergency_pos).upper():
        return False
    # Required coverage should not cannibalize an optimized starter.
    if _owner_key(name) in starter_keys:
        return False
    # Unknown reserve timelines stay protected; a known return horizon (e.g. Tank Dell
    # eligible Week 5) may be evaluated as a stash-release option.
    if "VERIFIED RESERVE" in prot and _v740_reserve_return_week(drop_row)<=0:
        return False
    # Extreme-value bench assets remain off limits even in an emergency.
    if cost>=35.0:
        return False
    return True

# ---------------- V7.38 Emergency Drop Ranking ----------------
def _v738_emergency_drop_rank(drop_row, roster_df, starter_names, emergency_pos):
    """Rank the *least damaging* cut for required-position coverage.

    V7.40 makes this a true bench/stash ranking instead of treating every CORE HOLD or
    reserve label as untouchable. Lower is safer to cut. Current starters and the player
    at the emergency position remain impossible cuts; active bench assets keep their ROS
    value, while confirmed multi-week absences receive an availability discount.
    """
    req={"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DL":1,"DB":1}
    bad={"OUT","DOUBTFUL","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"}
    name=str(drop_row.get("player",drop_row.get("Player","")) or "")
    pos=str(drop_row.get("position",drop_row.get("Position",drop_row.get("Pos",""))) or "").upper()
    prot=str(_v682_drop_protection(drop_row) or "")
    status=_v677_normalize_injury_status(drop_row.get("injury_effective",drop_row.get("injury","")))
    score=float(_v711_drop_asset_cost(drop_row,starter_names))
    starter_keys={_owner_key(x) for x in (starter_names or [])}

    if pos==str(emergency_pos).upper():
        return 999.0
    if _owner_key(name) in starter_keys:
        return 999.0

    # Protection is now a penalty, not an automatic veto, for bench players. This is the
    # key fix for the Kamara-only bug: stale CORE HOLD labels no longer hide every other
    # legitimate bench cut from the emergency ranking.
    if "CORE HOLD" in prot:
        score += 24.0
    elif "PREFER HOLD" in prot:
        score += 8.0

    # Confirmed reserve absences can be sacrificed when a required starting slot would
    # otherwise be empty. Known return horizon matters: more weeks unavailable means a
    # larger short-term discount, while unknown reserve timelines stay effectively held.
    return_week=_v740_reserve_return_week(drop_row)
    try:
        current_week=int((_v678_live_week or {}).get("week",1) or 1)
    except Exception:
        current_week=1
    if "VERIFIED RESERVE" in prot:
        if return_week<=0:
            return 999.0
        weeks_out=max(1,return_week-current_week)
        score -= min(24.0,10.0+3.5*weeks_out)
        score += 6.0  # retain some stash value instead of treating IR as dead weight
    elif status=="OUT":
        score -= 7.0
    elif status=="DOUBTFUL":
        score -= 3.0

    # Count playable roster depth at the candidate's position *after* this cut.
    if isinstance(roster_df,pd.DataFrame) and len(roster_df):
        sub=roster_df[roster_df["position"].astype(str).str.upper().eq(pos)]
        playable=[]
        for _,r in sub.iterrows():
            stx=_v677_normalize_injury_status(r.get("injury_effective",r.get("injury","")))
            if stx not in bad and _owner_key(r.get("player",""))!=_owner_key(name):
                playable.append(r)
        remaining=len(playable)
        floor=req.get(pos,0)
        if remaining < floor:
            score += 75.0
        elif remaining == floor:
            # V7.47 root fix: reaching the bare starting minimum is NOT surplus.
            # V7.38 accidentally rewarded this state (e.g. cutting an RB and leaving
            # exactly two playable RBs), which made thin positions look expendable.
            score += 28.0 if pos in ("RB","WR") else 18.0
        else:
            surplus=max(0,remaining-floor)
            if surplus==1:
                score += 8.0 if pos in ("RB","WR") else 3.0
            elif pos in ("DL","DB","QB"):
                score -= min(18.0,4.0+4.0*(surplus-1))
            elif pos in ("RB","WR"):
                score -= min(9.0,2.0+2.0*(surplus-2))
            elif pos=="K" and remaining>=1:
                score -= 5.0

    return round(max(0.0,score),2)

def _v746_drop_explanation(drop_row, roster_df, starter_names=None, emergency_pos=""):
    """Human-readable audit trail for why this player is the proposed cut."""
    name=str(drop_row.get("player",drop_row.get("Player","")) or "")
    pos=str(drop_row.get("position",drop_row.get("Position",drop_row.get("Pos",""))) or "").upper()
    tier=_v745_drop_tier(drop_row,starter_names)
    cost=_v711_drop_asset_cost(drop_row,starter_names)
    ros=_v682_ros_value(drop_row)
    market=_v712_row_num(drop_row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)
    starter_keys={_owner_key(x) for x in (starter_names or [])}
    reasons=[]
    reasons.append("bench asset" if _owner_key(name) not in starter_keys else "current optimized starter")
    reasons.append(f"{tier.lower()} tier")
    if market<=160: reasons.append(f"strong market value ({market:.0f})")
    elif market<999: reasons.append(f"market rank {market:.0f}")
    reasons.append(f"ROS {ros:.1f}")
    reasons.append(f"drop cost {cost:.1f}")
    if isinstance(roster_df,pd.DataFrame) and len(roster_df):
        same=roster_df[roster_df["position"].astype(str).str.upper().eq(pos)]
        playable=0
        for _,r in same.iterrows():
            if _owner_key(r.get("player",""))==_owner_key(name): continue
            stx=_v677_normalize_injury_status(r.get("injury_effective",r.get("injury","")))
            if stx not in ("OUT","DOUBTFUL","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
                playable+=1
        reasons.append(f"{playable} playable {pos} remain")
        _floor={"QB":1,"RB":2,"WR":2,"TE":1,"K":1,"DL":1,"DB":1}.get(pos,0)
        if playable<=_floor:
            reasons.append("would leave roster at/below required positional floor")
        elif playable==_floor+1:
            reasons.append("would leave only one reserve above positional floor")
    if emergency_pos: reasons.append(f"evaluated to cover required {str(emergency_pos).upper()}")
    return "; ".join(reasons)


def _v746_emergency_asset_ok(add_row, drop_row, net_week, net_ros, starter_names=None):
    """Emergency coverage cannot turn a valuable roster asset into a free pass.

    A required-position hole relaxes the *need* threshold, not asset preservation.
    """
    cost=_v711_drop_asset_cost(drop_row,starter_names)
    add_strength=_v712_add_asset_strength(add_row)
    drop_market=_v712_row_num(drop_row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)
    add_market=_v712_row_num(add_row,["market_pick","Market_pick","market_rank","Market Rank"],999.0)
    tier=_v745_drop_tier(drop_row,starter_names)
    nw=float(net_week); nr=float(net_ros)
    credit=max(0.0,nw)*8.0 + max(0.0,nr)*4.0
    # Valuable/market-relevant assets require the incoming player to compensate for the cut.
    if tier=="PROTECTED":
        return False,"HOLD — emergency coverage cannot cut a protected asset",cost
    if drop_market<=160 and add_market>drop_market+35 and nr<3.0:
        return False,"HOLD — emergency add is too weak for the outgoing market asset",cost
    if cost>=25.0 and cost > add_strength + credit + 4.0:
        return False,"HOLD — emergency add does not justify roster-asset cost",cost
    if cost>=35.0 and nr<2.0:
        return False,"HOLD — preserve high-value bench asset",cost
    return True,"",cost

def _v682_weekly_band(row):
    val=_v676_player_value(row)
    status=_v677_normalize_injury_status(row.get("injury",""))
    practice=str(row.get("practice_status","") or "").upper()
    matchup=str(row.get("_matchup_grade","") or "").upper()
    floor_mult=0.78
    ceil_mult=1.22
    if status=="QUESTIONABLE":
        floor_mult-=0.10; ceil_mult-=0.04
    elif status=="DOUBTFUL":
        floor_mult-=0.22; ceil_mult-=0.12
    elif status in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return 0.0,0.0
    if "DNP" in practice or "DID NOT PARTICIPATE" in practice:
        floor_mult-=0.06
    elif "LIMIT" in practice:
        floor_mult-=0.03
    if matchup=="GREAT":
        ceil_mult+=0.08
    elif matchup=="GOOD":
        ceil_mult+=0.04
    elif matchup=="TOUGH":
        floor_mult-=0.05
        ceil_mult-=0.05
    return max(0.0,val*max(0.35,floor_mult)), max(0.0,val*max(0.60,ceil_mult))

def _v682_start_confidence(row, edge=0.0):
    status=_v677_normalize_injury_status(row.get("injury",""))
    practice=str(row.get("practice_status","") or "").upper()
    matchup=str(row.get("_matchup_grade","") or "").upper()
    c=66.0 + max(-18.0,min(22.0,float(edge)*7.0))
    if status=="QUESTIONABLE": c-=12
    elif status=="DOUBTFUL": c-=28
    elif status in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"): c=2
    if "DNP" in practice or "DID NOT PARTICIPATE" in practice: c-=8
    elif "LIMIT" in practice: c-=4
    elif "FULL" in practice: c+=3
    if matchup=="GREAT": c+=5
    elif matchup=="GOOD": c+=2
    elif matchup=="TOUGH": c-=5
    return int(max(2,min(98,round(c))))

def _v682_decision(conf, edge, status):
    s=_v677_normalize_injury_status(status)
    if s in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return "⛔ AVOID"
    if s=="DOUBTFUL":
        return "🚨 SIT / BACKUP PLAN"
    if conf>=88 and edge>=1.0:
        return "🔒 LOCK"
    if conf>=76 and edge>=0.35:
        return "✅ START"
    if conf>=64 and edge>=0:
        return "🟢 LEAN START"
    if edge>-0.65:
        return "🟡 TOSS-UP"
    return "🪑 SIT"

def _v682_eligible_bench(starter_row, bench_df):
    if bench_df is None or bench_df.empty:
        return bench_df
    pos=str(starter_row.get("Pos",""))
    slot=str(starter_row.get("Slot",""))
    b=bench_df.copy()
    if slot.startswith("FLEX"):
        return b[b["position"].isin(["RB","WR","TE"])]
    return b[b["position"].eq(pos)]

def _v719_external_projection_valid(row):
    """Return True only when the external weekly projection is comparable to league scoring.

    Sleeper external projections are useful for offense/K, but IDP scoring formats vary too
    widely to treat a tiny/mismatched external number as a real consensus disagreement.
    Until an IDP-scoring-compatible external source is configured, DL/DB comparisons are N/A.
    """
    pos=str(row.get("position",row.get("Pos","")) or "").upper()
    ext=_v682_num(row,"_external_week_projection",0)
    if ext<=0:
        return False
    if pos in ("DL","DB","LB","DE","DT","S","CB"):
        return False
    return True

def _v719_best_alternative(starter_row, bench_df):
    """Return the best *playable* slot-eligible bench alternative, or None.

    V7.20 hardens V7.19 by excluding OUT/IR/PUP/NFI/SUSPENDED/DND players
    before ranking alternatives. Verified reserve identity is authoritative even
    when a stale display row still says Active.
    """
    elig=_v682_eligible_bench(starter_row,bench_df)
    if elig is None or elig.empty:
        return None
    x=elig.copy()
    unavailable={"OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"}
    def _playable(r):
        key=_owner_key(r.get("player",r.get("Player","")))
        fixed=_V679_VERIFIED_RESERVE.get(key,{}) if isinstance(_V679_VERIFIED_RESERVE,dict) else {}
        fixed_status=_v677_normalize_injury_status(fixed.get("status","")) if fixed else "ACTIVE"
        raw=r.get("injury_effective",r.get("injury",r.get("Status","")))
        status=fixed_status if fixed_status in unavailable else _v677_normalize_injury_status(raw)
        return status not in unavailable
    x=x[x.apply(_playable,axis=1)].copy()
    if x.empty:
        return None
    x["_start_value"]=pd.to_numeric(x.get("_start_value"),errors="coerce").fillna(0.0)
    return x.sort_values("_start_value",ascending=False).iloc[0]

def _v720_decision(conf, edge, status, has_alternative=True):
    """Decision semantics that distinguish projection confidence from roster choice."""
    s=_v677_normalize_injury_status(status)
    if s in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return "⛔ AVOID"
    if s=="DOUBTFUL":
        return "🚨 SIT / BACKUP PLAN"
    if not has_alternative:
        return "✅ START — NO ALTERNATIVE"
    return _v682_decision(conf,edge,status)

def _v682_injury_risk(row):
    status=_v677_normalize_injury_status(row.get("injury",""))
    practice=str(row.get("practice_status","") or "").upper()
    if status in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return "🔴 UNAVAILABLE"
    if status=="DOUBTFUL":
        return "🔴 HIGH"
    if status=="QUESTIONABLE":
        if "DNP" in practice: return "🟠 HIGH"
        if "LIMIT" in practice: return "🟡 MODERATE"
        return "🟡 WATCH"
    if "DNP" in practice:
        return "🟡 WATCH"
    if "LIMIT" in practice:
        return "🟡 LOW-MOD"
    return "🟢 LOW"

def _v682_injury_action(row):
    status=_v677_normalize_injury_status(row.get("injury",""))
    practice=str(row.get("practice_status","") or "").upper()
    protection=_v682_drop_protection(row)
    if status in ("IR","PUP","NFI"):
        return "IR STASH / HOLD" if protection else "IR STASH / REASSESS"
    if status=="OUT":
        return "BENCH — FIND REPLACEMENT"
    if status=="DOUBTFUL":
        return "PLAN ALTERNATIVE"
    if status=="QUESTIONABLE":
        return "MONITOR CLOSELY"
    if "DNP" in practice:
        return "WATCH PRACTICE / BACKUP READY"
    if "LIMIT" in practice:
        return "MONITOR"
    return "NO ACTION"

def _v682_injury_impact(row):
    status=_v677_normalize_injury_status(row.get("injury",""))
    practice=str(row.get("practice_status","") or "").upper()
    if status in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return "Starter unavailable"
    if status=="DOUBTFUL":
        return "Major availability risk"
    if status=="QUESTIONABLE":
        return "Start value discounted"
    if "DNP" in practice:
        return "Active, but workload/availability risk"
    if "LIMIT" in practice:
        return "Small workload risk"
    return "Minimal current impact"

def _v682_move_action(net_week, net_ros, add_row):
    add_ros=_v682_ros_value(add_row)
    if net_week>=1.5 or net_ros>=1.75:
        return "🔥 PRIORITY CLAIM"
    if net_week>=0.65 or net_ros>=0.85:
        return "⬆️ ADD"
    if net_ros>=0.30 and add_ros>0:
        return "🧳 STASH"
    if net_week>0.05 or net_ros>0.05:
        return "👀 WATCH"
    return "⛔ PASS"

def _v682_move_reason(net_week, net_ros, add_row, drop_row):
    parts=[]
    if net_week>=1.0: parts.append("clear weekly lineup gain")
    elif net_week>0.10: parts.append("small weekly gain")
    else: parts.append("depth/ROS move")
    if net_ros>=1.0: parts.append("strong ROS upgrade")
    elif net_ros>=0.30: parts.append("positive ROS upgrade")
    if _v682_ros_value(add_row) > _v682_ros_value(drop_row)+0.75:
        parts.append("better long-term value")
    if _v676_injury_multiplier(drop_row.get("injury",""),drop_row.get("practice_status","")) < _v676_injury_multiplier(add_row.get("injury",""),add_row.get("practice_status","")):
        parts.append("health upgrade")
    if _v682_drop_protection(drop_row):
        parts.append("⚠️ protected player")
    return " • ".join(parts)


# ---------------- V6.84 recommendation tracking + grading ----------------
def _v684_snapshot_key(season,week):
    return f"{int(season)}-W{int(week):02d}"

@st.cache_data(ttl=21600, show_spinner=False)
def _v684_week_actuals(season,week,idp_cfg_json="{}"):
    """
    Weekly actual fantasy output used only for grading Fantasy Edge decisions.
    Offense uses nflverse fantasy_points_ppr when available.
    IDP is calculated from available defensive stat fields using league settings.
    """
    try:
        yr=int(season); wk=int(week)
        cfg=json.loads(idp_cfg_json or "{}")
        url=f"https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_week_{yr}.csv"
        x=pd.read_csv(url,low_memory=False)
        if x is None or x.empty or "week" not in x.columns:
            return pd.DataFrame()

        if "season_type" in x.columns:
            x=x[x["season_type"].astype(str).str.upper().eq("REG")].copy()
        x["week"]=pd.to_numeric(x["week"],errors="coerce")
        x=x[x["week"].eq(wk)].copy()
        if x.empty:
            return pd.DataFrame()

        name_col=next((c for c in ["player_display_name","player_name","display_name","full_name","player"] if c in x.columns),None)
        if not name_col:
            return pd.DataFrame()

        if "position" not in x.columns:
            x["position"]=""
        x["position"]=x["position"].astype(str).map(canonical_position)

        def n(c):
            return pd.to_numeric(x[c],errors="coerce").fillna(0.0) if c in x.columns else pd.Series(0.0,index=x.index)

        offense=n("fantasy_points_ppr")

        # Schema-tolerant IDP scoring.
        solo=n("def_tackles_solo") if "def_tackles_solo" in x.columns else n("tackles_solo")
        assist=n("def_tackles_with_assist") if "def_tackles_with_assist" in x.columns else (
            n("tackles_assists") if "tackles_assists" in x.columns else n("assists")
        )
        sacks=n("def_sacks") if "def_sacks" in x.columns else n("sacks")
        tfl=n("def_tackles_for_loss") if "def_tackles_for_loss" in x.columns else n("tackles_for_loss")
        qb_hit=n("def_qb_hits") if "def_qb_hits" in x.columns else n("qb_hits")
        ints=n("def_interceptions") if "def_interceptions" in x.columns else n("interceptions")
        pdv=n("def_pass_defended") if "def_pass_defended" in x.columns else (
            n("passes_defended") if "passes_defended" in x.columns else n("pass_deflections")
        )
        ff=n("def_fumbles_forced") if "def_fumbles_forced" in x.columns else n("fumbles_forced")
        fr=n("def_fumbles") if "def_fumbles" in x.columns else (
            n("fumbles_recovered") if "fumbles_recovered" in x.columns else pd.Series(0.0,index=x.index)
        )
        td=n("def_tds") if "def_tds" in x.columns else n("defensive_tds")
        saf=n("def_safeties") if "def_safeties" in x.columns else n("safeties")

        idp=(
            solo*float(cfg.get("solo",1.5))
            + assist*float(cfg.get("assist",0.75))
            + sacks*float(cfg.get("sack",4.0))
            + tfl*float(cfg.get("tfl",2.0))
            + qb_hit*float(cfg.get("qb_hit",0.0))
            + ints*float(cfg.get("int",7.0))
            + pdv*float(cfg.get("pd",2.0))
            + ff*float(cfg.get("ff",4.0))
            + fr*float(cfg.get("fr",4.0))
            + td*float(cfg.get("def_td",12.0))
            + saf*float(cfg.get("safety",8.0))
        )

        x["_actual"]=offense
        x.loc[x["position"].isin(["DL","DB"]),"_actual"]=idp[x["position"].isin(["DL","DB"])]

        out=pd.DataFrame({
            "player":x[name_col].astype(str).str.strip(),
            "position":x["position"].astype(str),
            "actual":pd.to_numeric(x["_actual"],errors="coerce")
        })
        out=out[out["player"].ne("") & out["actual"].notna()].copy()
        out["_key"]=out["player"].map(_owner_key)
        # Some sources can have duplicate rows; aggregate safely.
        out=out.groupby(["_key","player","position"],as_index=False)["actual"].sum()
        return out
    except Exception as e:
        pass  # cached loaders must not mutate session_state
        return pd.DataFrame()

def _v684_build_snapshot(board_df,state,season,week,waiver_df=None):
    my=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty:
        return None

    starters,bench,lineup_score=_v676_optimize_lineup(my)
    calls=[]
    for _,sr in starters.iterrows():
        src=my[my["player"].eq(sr["Player"])]
        src=src.iloc[0] if len(src) else pd.Series(dtype=object)
        elig=_v682_eligible_bench(sr,bench)
        if elig is not None and len(elig):
            br=elig.sort_values("_start_value",ascending=False).iloc[0]
            alt=str(br.get("player",""))
            alt_value=float(br.get("_start_value",0) or 0)
        else:
            alt=""
            alt_value=0.0

        edge=float(sr.get("Adjusted PPG",0) or 0)-alt_value
        conf=_v716_start_confidence(src,edge,state.get("recommendation_history",[]),state)
        calls.append({
            "slot":str(sr.get("Slot","")),
            "starter":str(sr.get("Player","")),
            "starter_pos":str(sr.get("Pos","")),
            "alternative":alt,
            "edge":round(edge,3),
            "confidence":int(conf),
            "decision":_v682_decision(conf,edge,src.get("injury","")),
            "projection":round(_v682_num(src,"projection",0),3),
            "external_projection":round(_v682_num(src,"_external_week_projection",0),3) if _v719_external_projection_valid(src) else None,
            "adjusted_projection":round(_v676_player_value(src),3),
            "matchup_adjustment":round(_v682_num(src,"_matchup_adjustment",0),3),
            "role_adjustment":round(_v683_role_adjustment(src),3),
            "role_trend":str(src.get("_role_trend","") or ""),
            "recent_ppg3":round(_v682_num(src,"_recent_ppg3",0),3),
            "injury":_v677_normalize_injury_status(src.get("injury","")),
            "practice":str(src.get("practice_status","") or "")
        })

    waivers=[]
    if isinstance(waiver_df,pd.DataFrame) and not waiver_df.empty:
        for _,r in waiver_df.head(12).iterrows():
            waivers.append({
                "add":str(r.get("Add","")),
                "drop":str(r.get("Drop","")),
                "position":str(r.get("Pos","")),
                "action":str(r.get("Action","")),
                "net_week":round(float(pd.to_numeric(pd.Series([r.get("Net Week",0)]),errors="coerce").fillna(0).iloc[0]),3),
                "net_ros":round(float(pd.to_numeric(pd.Series([r.get("Net ROS",0)]),errors="coerce").fillna(0).iloc[0]),3),
                "add_projection":round(float(pd.to_numeric(pd.Series([r.get("Add PPG",0)]),errors="coerce").fillna(0).iloc[0]),3),
                "drop_projection":round(float(pd.to_numeric(pd.Series([r.get("Drop PPG",0)]),errors="coerce").fillna(0).iloc[0]),3),
                "add_role":str(r.get("Add Role","") or "")
            })

    role_watch=[]
    role_pool=board_df[
        board_df["_role_trend"].astype(str).str.contains("RISING|FALLING",regex=True,na=False)
    ].copy() if "_role_trend" in board_df.columns else pd.DataFrame()
    if len(role_pool):
        role_pool["_abs_role_delta"]=pd.to_numeric(role_pool.get("_role_delta",0),errors="coerce").fillna(0).abs()
        role_pool=role_pool.sort_values(["_abs_role_delta","projection"],ascending=False).head(30)
        for _,r in role_pool.iterrows():
            role_watch.append({
                "player":str(r.get("player","")),
                "position":str(r.get("position","")),
                "trend":str(r.get("_role_trend","")),
                "role_delta":round(_v682_num(r,"_role_delta",0),3),
                "recent_ppg3":round(_v682_num(r,"_recent_ppg3",0),3),
                "projection":round(_v682_num(r,"projection",0),3)
            })

    return {
        "key":_v684_snapshot_key(season,week),
        "season":int(season),
        "week":int(week),
        "saved_at":datetime.now(timezone.utc).isoformat(),
        "lineup_projection":round(float(lineup_score),3),
        "start_sit":calls,
        "waivers":waivers,
        "role_watch":role_watch
    }

def _v684_grade_snapshot(snapshot,state):
    if not isinstance(snapshot,dict):
        return None
    season=int(snapshot.get("season",0) or 0)
    week=int(snapshot.get("week",0) or 0)
    actuals=_v684_week_actuals(season,week,json.dumps(state.get("idp",{}),sort_keys=True))
    if actuals is None or actuals.empty:
        return {
            "ready":False,"season":season,"week":week,
            "reason":"Weekly actuals are not available yet."
        }

    amap={str(r["_key"]):float(r["actual"]) for _,r in actuals.iterrows()}

    decisions=[]
    raw_errors=[]
    adjusted_errors=[]
    matchup_help=[]
    confidence_rows=[]

    for c in snapshot.get("start_sit",[]) or []:
        sk=_owner_key(c.get("starter",""))
        ak=_owner_key(c.get("alternative",""))
        if sk not in amap:
            continue
        sa=amap[sk]
        proj=float(c.get("projection",0) or 0)
        adj=float(c.get("adjusted_projection",proj) or proj)
        raw_err=abs(sa-proj)
        adj_err=abs(sa-adj)
        raw_errors.append(raw_err)
        adjusted_errors.append(adj_err)
        if abs(float(c.get("matchup_adjustment",0) or 0))>=0.05:
            matchup_help.append(1 if adj_err < raw_err else 0)

        row={
            "Slot":c.get("slot",""),
            "Start":c.get("starter",""),
            "Alternative":c.get("alternative",""),
            "Confidence":int(c.get("confidence",0) or 0),
            "Projected":round(proj,2),
            "Adjusted":round(adj,2),
            "Actual Start":round(sa,2),
            "Actual Alternative":None,
            "Correct":None,
            "Margin":None
        }
        if ak and ak in amap:
            aa=amap[ak]
            correct=sa>=aa
            row["Actual Alternative"]=round(aa,2)
            row["Correct"]="✅" if correct else "❌"
            row["Margin"]=round(sa-aa,2)
            confidence_rows.append((int(c.get("confidence",0) or 0),1 if correct else 0))
        decisions.append(row)

    scored=[r for r in decisions if r["Correct"] in ("✅","❌")]
    correct=sum(1 for r in scored if r["Correct"]=="✅")

    waiver_rows=[]
    for w in snapshot.get("waivers",[]) or []:
        addk=_owner_key(w.get("add","")); dropk=_owner_key(w.get("drop",""))
        if addk not in amap:
            continue
        add_actual=amap[addk]
        drop_actual=amap.get(dropk)
        win=(drop_actual is not None and add_actual>drop_actual)
        waiver_rows.append({
            "Action":w.get("action",""),
            "Add":w.get("add",""),
            "Drop":w.get("drop",""),
            "Net Week":w.get("net_week",0),
            "Net ROS":w.get("net_ros",0),
            "Add Actual":round(add_actual,2),
            "Drop Actual":None if drop_actual is None else round(drop_actual,2),
            "This-Week Win":None if drop_actual is None else ("✅" if win else "❌")
        })

    role_rows=[]
    for r in snapshot.get("role_watch",[]) or []:
        k=_owner_key(r.get("player",""))
        if k not in amap:
            continue
        actual=amap[k]
        baseline=float(r.get("recent_ppg3",0) or 0)
        trend=str(r.get("trend",""))
        if baseline<=0:
            follow=None
        elif "RISING" in trend:
            follow=actual>=baseline
        elif "FALLING" in trend:
            follow=actual<=baseline
        else:
            follow=None
        role_rows.append({
            "Player":r.get("player",""),
            "Trend":trend,
            "Prior 3 PPG":round(baseline,2),
            "Actual":round(actual,2),
            "Follow-through":None if follow is None else ("✅" if follow else "❌")
        })

    conf_hi=[v for c,v in confidence_rows if c>=76]
    role_scored=[r for r in role_rows if r["Follow-through"] in ("✅","❌")]
    waiver_scored=[r for r in waiver_rows if r["This-Week Win"] in ("✅","❌")]

    return {
        "ready":True,
        "season":season,"week":week,
        "decisions":decisions,
        "start_sit_scored":len(scored),
        "start_sit_correct":correct,
        "start_sit_accuracy":(correct/len(scored)*100) if scored else None,
        "projection_mae":(sum(raw_errors)/len(raw_errors)) if raw_errors else None,
        "adjusted_mae":(sum(adjusted_errors)/len(adjusted_errors)) if adjusted_errors else None,
        "matchup_help_rate":(sum(matchup_help)/len(matchup_help)*100) if matchup_help else None,
        "high_conf_accuracy":(sum(conf_hi)/len(conf_hi)*100) if conf_hi else None,
        "waivers":waiver_rows,
        "waiver_scored":len(waiver_scored),
        "waiver_wins":sum(1 for r in waiver_scored if r["This-Week Win"]=="✅"),
        "role_rows":role_rows,
        "role_scored":len(role_scored),
        "role_hits":sum(1 for r in role_scored if r["Follow-through"]=="✅")
    }

def _v684_history_summary(history,state):
    rows=[]
    for snap in history or []:
        g=_v684_grade_snapshot(snap,state)
        if not g or not g.get("ready"):
            continue
        rows.append({
            "Week":f"{g['season']} W{g['week']}",
            "Start/Sit Accuracy":None if g["start_sit_accuracy"] is None else round(g["start_sit_accuracy"],1),
            "Projection MAE":None if g["projection_mae"] is None else round(g["projection_mae"],2),
            "Adjusted MAE":None if g["adjusted_mae"] is None else round(g["adjusted_mae"],2),
            "Matchup Help %":None if g["matchup_help_rate"] is None else round(g["matchup_help_rate"],1),
            "High Conf %":None if g["high_conf_accuracy"] is None else round(g["high_conf_accuracy"],1),
            "Waiver Wins":f"{g['waiver_wins']}/{g['waiver_scored']}" if g["waiver_scored"] else "—",
            "Role Hits":f"{g['role_hits']}/{g['role_scored']}" if g["role_scored"] else "—"
        })
    return pd.DataFrame(rows)


# ---------------- V6.86-V6.91 intelligence helpers ----------------
def _v686_idp_intelligence(row):
    pos=str(row.get("position","") or "")
    if pos not in ("DL","DB"): return 0.0,"N/A"
    proj=_v682_num(row,"projection",0); recent=_v682_num(row,"_recent_ppg3",0)
    role=_v683_role_adjustment(row); matchup=_v682_num(row,"_matchup_adjustment",0); vorp=_v682_num(row,"vorp",0)
    score=proj*.45+recent*.30+role*2+matchup*1.2+max(-2,min(4,vorp))*.5
    tier="ELITE START" if score>=14 else "STRONG START" if score>=10 else "STARTABLE" if score>=7 else "MATCHUP PLAY" if score>=4.5 else "BENCH / WATCH"
    return round(score,2),tier


# ---------------- V6.95-V6.98 automation, calibration and action engine ----------------
def _v695_game_window_tag(now_local=None):
    now_local=now_local or datetime.now()
    wd=now_local.weekday(); hr=now_local.hour
    if wd==3 and 14<=hr<=23: return "THU_PREGAME"
    if wd==6 and 7<=hr<=12: return "SUN_AM"
    if wd==6 and 12<=hr<=15: return "SUN_FINAL"
    return ""

def _v695_autosave_snapshot(board_df,state,season,week,waiver_df=None):
    tag=_v695_game_window_tag()
    if not tag: return False,None
    snap=_v684_build_snapshot(board_df,state,season,week,waiver_df)
    if not snap: return False,None
    snap["checkpoint"]=tag
    snap["key"]=f"{_v684_snapshot_key(season,week)}-{tag}"
    hist=state.setdefault("recommendation_history",[])
    if any(str(s.get("key",""))==snap["key"] for s in hist if isinstance(s,dict)):
        return False,snap["key"]
    hist.append(snap)
    state["recommendation_history"]=sorted(hist,key=lambda s:(int(s.get("season",0)),int(s.get("week",0)),str(s.get("checkpoint",""))))
    save_state(state)
    return True,snap["key"]

def _v696_confidence_bins(history,state):
    rows=[]
    for snap in history or []:
        g=_v684_grade_snapshot(snap,state)
        if not g or not g.get("ready"): continue
        for d in g.get("decisions",[]) or []:
            if d.get("Correct") not in ("✅","❌"): continue
            conf=int(d.get("Confidence",0) or 0)
            bucket="85-100" if conf>=85 else ("70-84" if conf>=70 else ("55-69" if conf>=55 else "<55"))
            rows.append({"Bucket":bucket,"Confidence":conf,"Correct":1 if d.get("Correct")=="✅" else 0})
    if not rows: return pd.DataFrame()
    x=pd.DataFrame(rows)
    out=x.groupby("Bucket",as_index=False).agg(Calls=("Correct","size"),Actual=("Correct","mean"),Avg=("Confidence","mean"))
    out["Actual Accuracy %"]=(out["Actual"]*100).round(1)
    out["Avg Confidence %"]=out["Avg"].round(1)
    out["Calibration Gap"]=(out["Avg Confidence %"]-out["Actual Accuracy %"]).round(1)
    out["Status"]=out["Calibration Gap"].apply(lambda g:"OVERCONFIDENT" if g>=10 else ("UNDERCONFIDENT" if g<=-10 else "WELL CALIBRATED"))
    order=["85-100","70-84","55-69","<55"]
    out["Bucket"]=pd.Categorical(out["Bucket"],categories=order,ordered=True)
    return out.sort_values("Bucket")[["Bucket","Calls","Avg Confidence %","Actual Accuracy %","Calibration Gap","Status"]]

def _v696_calibrated_confidence(raw_conf,history,state):
    try: raw=int(raw_conf)
    except Exception: raw=50
    bins=_v696_confidence_bins(history,state)
    if bins.empty: return raw
    bucket="85-100" if raw>=85 else ("70-84" if raw>=70 else ("55-69" if raw>=55 else "<55"))
    sub=bins[bins["Bucket"].astype(str).eq(bucket)]
    if sub.empty or int(sub.iloc[0]["Calls"])<5: return raw
    actual=float(sub.iloc[0]["Actual Accuracy %"])
    return int(round(max(2,min(98,0.65*raw+0.35*actual))))

def _v703_need_adjustment(position,roster_df,state):
    """V7.06 roster-fit adjustment: suppress luxury depth when actual needs exist elsewhere."""
    pos=str(position or "").upper()
    counts=roster_df["position"].astype(str).value_counts().to_dict() if isinstance(roster_df,pd.DataFrame) and len(roster_df) else {}
    have=int(counts.get(pos,0)); slots=state.get("roster_slots",{}) or {}
    required=int(slots.get(pos,0) or 0)

    if have<required:
        return 8.0,"Critical need"

    # Single-starter positions should not crowd the top of waivers merely as luxury depth.
    if pos in ("QB","TE") and required:
        if have>=required+1:
            return -8.0,"Position depth already covered"
        if have>=required:
            return -4.0,"Starter already covered"

    if pos=="K" and required and have>=required:
        return -10.0,"Kicker already covered"

    if pos in ("DL","DB"):
        if have>=required+1:
            return -10.0,"IDP depth already covered"
        if have>=required:
            return -5.0,"IDP starter already covered"

    if pos in ("RB","WR"):
        flex=int(slots.get("FLEX",0) or 0)
        target=required+max(1,(flex+1)//2)+1
        if have<required+1:
            return 5.0,"Roster need"
        if have>=target+2:
            return -5.0,"Deep position already"

    return 0.0,"Balanced"

def _v703_evidence_quality(row):
    evidence=0
    if str(row.get("injury_source","") or "").strip() not in ("","Local"): evidence+=1
    if "NO MATCHUP" not in str(row.get("_matchup_source","") or "").upper() and str(row.get("_matchup_source","") or "").strip(): evidence+=1
    if _v682_num(row,"_usage_games",0)>0 and str(row.get("_usage_recency","") or "").upper()=="CURRENT": evidence+=1
    ext=row.get("_external_week_projection",np.nan)
    try:
        if ext is not None and not pd.isna(ext): evidence+=1
    except Exception:
        pass
    return evidence

def _v703_move_type(net_week,net_ros):
    if net_week>=0.75 and net_ros<0.75: return "Short-term streamer"
    if net_ros>=1.50 and net_week<0.50: return "Long-term stash"
    if net_week>=0.50 and net_ros>=1.00: return "Weekly + ROS upgrade"
    if net_ros>=0.40: return "ROS depth upgrade"
    return "Marginal / monitor"

def _v703_faab_guidance(score,label,state):
    budget=max(0,int(state.get("faab",100) or 0))
    if label=="🔥 PRIORITY CLAIM": pct=(15,25) if score>=92 else (10,15); claim="Use top claim" if score>=92 else "Claim if top 3"
    elif label=="⬆️ ADD NOW": pct=(5,10); claim="Submit standard claim"
    elif label=="🧳 STASH": pct=(1,3); claim="Low-cost claim"
    elif label=="🎯 STREAMER": pct=(0,2); claim="Use a low claim"
    else: pct=(0,0); claim="Do not burn priority"
    lo=round(budget*pct[0]/100); hi=round(budget*pct[1]/100)
    bid="$0" if hi==0 else (f"${hi}" if lo==hi else f"${lo}–${hi}")
    return bid,claim

def _v703_why_not(label,net_week,net_ros,need_label,evidence):
    if label=="🔥 PRIORITY CLAIM": return "—"
    reasons=[]
    if net_week<0.35: reasons.append("no clear lineup gain")
    if net_ros<0.75: reasons.append("limited ROS gain")
    if "covered" in need_label.lower() or "deep" in need_label.lower(): reasons.append(need_label.lower())
    if evidence<=1: reasons.append("evidence gate: only one live-data signal")
    return " • ".join(reasons[:3]) or "Useful, but below priority threshold"

def _v697_waiver_priority_score(add_row,drop_row,state,net_week=None,net_ros=None,net_roster=None,need_adjustment=0.0):
    """V7.06 claim urgency: transaction value + roster fit + a hard live-evidence gate."""
    if net_week is None: net_week=_v676_player_value(add_row)-_v676_player_value(drop_row)
    if net_ros is None: net_ros=_v682_ros_value(add_row)-_v682_ros_value(drop_row)
    if net_roster is None: net_roster=(float(net_week)+float(net_ros))/2.0
    net_week=float(net_week); net_ros=float(net_ros); net_roster=float(net_roster)
    role=max(-1.0,min(1.0,_v683_role_adjustment(add_row)))
    scarcity=float(add_row.get("_scarcity_score",0) or 0)/100.0
    drop_status=_v677_normalize_injury_status(drop_row.get("injury",""))
    drop_protection=_v682_drop_protection(drop_row)
    injury_bonus=1.0 if drop_status in ("OUT","IR","PUP","NFI","DOUBTFUL") and not drop_protection else 0.0
    position=str(add_row.get("position","") or "").upper()
    evidence=_v703_evidence_quality(add_row)
    emergency=(float(need_adjustment)>=7.0) or (injury_bonus>0)

    score=(42.0
           +max(-14.0,min(18.0,net_week*6.0))
           +max(-12.0,min(16.0,net_ros*4.0))
           +max(-8.0,min(8.0,net_roster*2.0))
           +max(-4.0,min(5.0,role*5.0))
           +max(0.0,min(4.0,scarcity*4.0))
           +injury_bonus*3.0
           +max(-10.0,min(8.0,float(need_adjustment))))

    # Luxury IDP/single-starter depth requires a real transaction gain to stay near the top.
    if position in ("DL","DB") and net_week<0.75 and net_ros<2.0: score-=8.0
    if position in ("QB","TE","K") and float(need_adjustment)<0 and net_week<0.50: score-=4.0

    meaningful=(net_week>=0.35 or net_ros>=0.75 or net_roster>=0.50)
    priority_gain=(net_week>=1.25 or net_ros>=2.0) and net_roster>=0.75
    if position in ("DL","DB"):
        priority_gain=priority_gain and (net_week>=0.75 or net_ros>=2.5)

    # HARD EVIDENCE GATE: weakly supported players cannot be ADD NOW / PRIORITY
    # unless this transaction addresses a critical roster hole or unavailable player.
    if evidence==0 and not emergency:
        score=min(score,57.0)
    elif evidence<=1 and not emergency:
        score=min(score,69.0)
    elif evidence<=1 and emergency:
        score=min(score,79.0)

    score=max(0.0,min(96.0,score))

    if score>=88 and priority_gain and evidence>=2:
        label="🔥 PRIORITY CLAIM"
    elif score>=72 and meaningful and (evidence>=2 or emergency):
        label="⬆️ ADD NOW"
    elif score>=62 and net_week<0.75 and net_ros>=0.40:
        label="🧳 STASH"
    elif score>=58 and net_week>=0.35:
        label="🎯 STREAMER"
    elif score>=48:
        label="👀 WATCH"
    else:
        label="⛔ PASS"

    # Defensive final guard against any future scoring change bypassing evidence policy.
    if evidence<=1 and not emergency and label in ("🔥 PRIORITY CLAIM","⬆️ ADD NOW"):
        label="🧳 STASH" if net_ros>=0.75 else ("🎯 STREAMER" if net_week>=0.35 else "👀 WATCH")

    # V7.07 HARD ROSTER-FIT GATE: luxury additions cannot be ADD NOW merely because
    # an injured player makes the arithmetic look favorable. Cross-position luxury
    # adds require a genuinely exceptional lineup + ROS improvement.
    need_adj=float(need_adjustment)
    cross_position=str(add_row.get("position","") or "") != str(drop_row.get("position","") or "")
    exceptional=(net_week>=1.50 and net_ros>=2.50 and net_roster>=1.25 and evidence>=2)
    if need_adj<=-4.0 and cross_position and not exceptional:
        score=min(score,67.0)
        label="🧳 STASH" if net_ros>=1.0 else ("🎯 STREAMER" if net_week>=0.50 else "👀 WATCH")
    if need_adj<=-8.0 and not exceptional:
        score=min(score,61.0)
        label="🧳 STASH" if net_ros>=1.25 else "👀 WATCH"
    return round(score,1),label

def _v698_action_queue(board_df,state,history,consensus_df=None,trade_ideas=None,limit=5):
    my=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty: return pd.DataFrame()
    actions=[]
    starters,bench,_=_v676_optimize_lineup(my)
    for _,s in starters.iterrows():
        p=str(s.get("Player","")); src=my[my["player"].eq(p)]
        if src.empty: continue
        r=src.iloc[0]; risk=_v682_injury_risk(r)
        if risk in ("HIGH","UNAVAILABLE","MODERATE"):
            urg=98 if risk=="UNAVAILABLE" else (90 if risk=="HIGH" else 80)
            actions.append({"Urgency":urg,"Type":"Injury","Action":f"{p}: {_v682_injury_action(r)}","Why":f"{_v677_normalize_injury_status(r.get('injury',''))} • {risk}"})
    fa=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="FA")].copy()
    if len(fa):
        weak=my.copy(); weak["_dropv"]=weak.apply(_v690_trade_value,axis=1); drop=weak.sort_values("_dropv").iloc[0]
        fa["_cand"]=fa.apply(_v690_trade_value,axis=1)
        for _,add in fa.sort_values("_cand",ascending=False).head(10).iterrows():
            score,label=_v697_waiver_priority_score(add,drop,state)
            if score>=64:
                actions.append({"Urgency":min(94,int(score)),"Type":"Waiver","Action":f"{label}: add {add['player']}","Why":f"Score {score}/100 • {_v683_role_summary(add)}"})
    if isinstance(consensus_df,pd.DataFrame) and not consensus_df.empty:
        c=consensus_df[consensus_df["player"].isin(my["player"]) & consensus_df["Consensus Flag"].eq("⚠️ MAJOR DISAGREEMENT")]
        for _,r in c.head(3).iterrows():
            actions.append({"Urgency":68,"Type":"Projection","Action":f"Review {r['player']} projection","Why":f"Fantasy Edge vs external: {float(r.get('FE vs External',0)):+.2f}"})
    if isinstance(trade_ideas,pd.DataFrame) and not trade_ideas.empty:
        tr=trade_ideas.iloc[0]
        if float(tr.get("Your Gain",0) or 0)>=0.75:
            actions.append({"Urgency":60,"Type":"Trade","Action":f"Offer {tr['You Give']} for {tr['You Get']}","Why":f"{tr['Partner']} • modeled gain {float(tr['Your Gain']):+.2f}"})
    if not actions: return pd.DataFrame()
    out=pd.DataFrame(actions).sort_values(["Urgency","Type"],ascending=[False,True]).drop_duplicates("Action")
    out["Priority"]=range(1,len(out)+1)
    return out[["Priority","Urgency","Type","Action","Why"]].head(limit)



# ---------------- V7.28 weekly decision intelligence ----------------
def _v728_decision_urgency(row, edge, confidence, has_alt=True):
    """Translate existing evidence into an action label without changing projections."""
    status=_v677_normalize_injury_status(row.get("injury_effective",row.get("injury","")))
    practice=str(row.get("practice_status","") or "").upper()
    try: edge=float(edge)
    except Exception: edge=99.0
    try: confidence=float(confidence)
    except Exception: confidence=50.0
    if status in ("OUT","IR","PUP","NFI","SUSPENDED","DO NOT DRAFT"):
        return "🔴 ACT NOW"
    if status=="DOUBTFUL" or (practice=="DNP" and has_alt and edge<=2.0):
        return "🔴 ACT NOW"
    if status=="QUESTIONABLE" or practice in ("DNP","LIMITED","PENDING"):
        return "🟡 MONITOR"
    if has_alt and (abs(edge)<=1.0 or confidence<60):
        return "🟡 REVIEW"
    return "🟢 NO ACTION"

def _v728_roster_impact(add_row, drop_row, my_df):
    """Whole-roster lineup impact of an add/drop using the existing legal lineup optimizer."""
    if add_row is None or drop_row is None or my_df is None or my_df.empty: return 0.0
    before=_v676_roster_score(my_df)
    after=my_df[~my_df["player"].eq(str(drop_row.get("player","")))].copy()
    after=pd.concat([after,pd.DataFrame([add_row])],ignore_index=True)
    return round(float(_v676_roster_score(after)-before),2)

def _v728_command_center(board_df,state,waiver_df=None,trade_df=None,limit=5):
    """Outcome-oriented weekly queue. Uses frozen engines; does not alter scoring."""
    my=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty: return pd.DataFrame()
    starters,bench,_=_v676_optimize_lineup(my)
    rows=[]
    for _,sr in starters.iterrows():
        src=my[my["player"].eq(sr.get("Player",""))]
        if src.empty: continue
        r=src.iloc[0]
        alt=_v719_best_alternative(sr,bench)
        has_alt=alt is not None
        edge=float(sr.get("Adjusted PPG",0))-float(alt.get("_start_value",0)) if has_alt else 99.0
        conf=_v716_start_confidence(r,edge if has_alt else 0,state.get("recommendation_history",[]),state)
        urgency=_v728_decision_urgency(r,edge,conf,has_alt)
        if urgency.startswith("🔴") or urgency.startswith("🟡"):
            alt_name=str(alt.get("player","")) if has_alt else "no active alternative"
            rows.append({"Priority":0,"Urgency":urgency,"Area":"LINEUP","Action":f"{sr.get('Player','')} vs {alt_name}","Why":f"{_v677_status_icon(r.get('injury_effective',r.get('injury','')))} • edge {'—' if not has_alt else f'{edge:+.2f}'} • {conf}% confidence"})
    # Only surface waiver moves already cleared by the final V7.14+ veto table.
    if isinstance(waiver_df,pd.DataFrame) and not waiver_df.empty:
        good=waiver_df[waiver_df.get("Waiver Call",pd.Series(index=waiver_df.index,dtype=str)).astype(str).str.contains("PRIORITY|ADD NOW",regex=True,na=False)]
        for _,r in good.head(2).iterrows():
            rows.append({"Priority":0,"Urgency":"🟡 REVIEW","Area":"WAIVER","Action":f"Add {r.get('Add','')} / drop {r.get('Drop','')}","Why":f"Week {float(r.get('Net Week',0) or 0):+.2f} • ROS {float(r.get('Net ROS',0) or 0):+.2f}"})
    if isinstance(trade_df,pd.DataFrame) and not trade_df.empty:
        for _,r in trade_df.head(1).iterrows():
            if float(r.get("Your Gain",0) or 0)>=1.0 and float(r.get("Partner Gain",0) or 0)>=-0.25:
                rows.append({"Priority":0,"Urgency":"🟢 OPTIONAL","Area":"TRADE","Action":f"Explore {r.get('You Give','')} → {r.get('You Get','')}","Why":f"Starting-roster gain {float(r.get('Your Gain',0)):+.2f}"})
    if not rows:
        return pd.DataFrame([{"Priority":1,"Urgency":"🟢 NO ACTION","Area":"ROSTER","Action":"No urgent roster move","Why":"Current lineup and transaction guards do not identify a worthwhile change."}])
    rank={"🔴 ACT NOW":0,"🟡 MONITOR":1,"🟡 REVIEW":2,"🟢 OPTIONAL":3,"🟢 NO ACTION":4}
    out=pd.DataFrame(rows); out["_r"]=out["Urgency"].map(rank).fillna(9)
    out=out.sort_values(["_r","Area"]).head(limit).drop(columns="_r")
    out["Priority"]=range(1,len(out)+1)
    return out[["Priority","Urgency","Area","Action","Why"]]

# ---------------- V7.15-V7.18 weekly intelligence suite ----------------
def _v715_validation_status(board_df,state,history,season,week):
    """Live validation state for the current week without changing core projections."""
    cur_role=0
    if isinstance(board_df,pd.DataFrame) and len(board_df):
        cur_role=int((board_df.get("_usage_recency",pd.Series(index=board_df.index,dtype=str)).astype(str)=="CURRENT").sum())
    graded=0
    ready=[]
    for snap in history or []:
        try:
            g=_v684_grade_snapshot(snap,state)
        except Exception:
            g=None
        if g and g.get("ready"):
            graded+=1; ready.append(g)
    return {
        "season":int(season),"week":int(week),"current_role_players":cur_role,
        "graded_weeks":graded,"latest_grade":ready[-1] if ready else None
    }


def _v715_weekly_changes(board_df,state,history,season,week,limit=12):
    """Compare the current roster against the latest saved recommendation checkpoint."""
    if board_df is None or board_df.empty: return pd.DataFrame()
    my=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty: return pd.DataFrame()
    snaps=[x for x in (history or []) if isinstance(x,dict) and int(x.get("season",0) or 0)==int(season)]
    snaps=sorted(snaps,key=lambda x:(int(x.get("week",0) or 0),str(x.get("saved_at",""))))
    base=snaps[-1] if snaps else None
    base_map={}
    if base:
        for c in base.get("start_sit",[]) or []:
            base_map[_owner_key(c.get("starter",""))]=c
    rows=[]
    for _,r in my.iterrows():
        name=str(r.get("player","")); key=_owner_key(name); b=base_map.get(key,{})
        cur_proj=_v682_num(r,"projection",0); old_proj=float(b.get("projection",cur_proj) or cur_proj)
        proj_delta=cur_proj-old_proj
        cur_status=_v677_normalize_injury_status(r.get("injury","")); old_status=str(b.get("injury",cur_status) or cur_status)
        cur_role=str(r.get("_role_trend","") or ""); old_role=str(b.get("role_trend",cur_role) or cur_role)
        ext=_v682_num(r,"_external_week_projection",0); ext_gap=(cur_proj-ext) if ext>0 else 0.0
        signals=[]; magnitude=0.0
        if abs(proj_delta)>=0.75: signals.append(f"Projection {proj_delta:+.1f}"); magnitude=max(magnitude,abs(proj_delta))
        if cur_status!=old_status: signals.append(f"Status {old_status} → {cur_status}"); magnitude=max(magnitude,3.0)
        if cur_role!=old_role and cur_role not in ("","NO LIVE ROLE DATA","HISTORICAL ROLE BASELINE"):
            signals.append(cur_role); magnitude=max(magnitude,2.0)
        if abs(ext_gap)>=2.5: signals.append(f"FE vs external {ext_gap:+.1f}"); magnitude=max(magnitude,abs(ext_gap)*.5)
        if signals:
            rows.append({"Player":name,"Pos":str(r.get("position","")),"Change":" • ".join(signals),"Impact":round(magnitude,2)})
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Impact",ascending=False).head(limit)


def _v716_start_confidence(row,edge,history,state):
    """Start/sit confidence using bench edge + matchup + role + external agreement + calibration."""
    raw=_v682_start_confidence(row,edge)
    adj=float(raw)
    ext=_v682_num(row,"_external_week_projection",0); fe=_v682_num(row,"projection",0)
    if _v719_external_projection_valid(row) and fe>0:
        gap=abs(fe-ext)
        if gap<=1.0: adj+=3
        elif gap>=4.0: adj-=8
        elif gap>=2.5: adj-=4
    role=str(row.get("_role_trend","") or "")
    if str(row.get("_usage_recency","")).upper()=="CURRENT":
        if "RISING" in role: adj+=3
        elif "FALLING" in role: adj-=4
    ma=_v682_num(row,"_matchup_adjustment",0)
    if ma>=1.0: adj+=2
    elif ma<=-1.0: adj-=2
    # V7.21: confirmed workload recovery can restore confidence even if a stale
    # QUESTIONABLE tag lingers; weak return usage remains appropriately uncertain.
    ramp=_v721_injury_return_multiplier(row)
    status=_v677_normalize_injury_status(row.get("injury_effective",row.get("injury","")))
    if status=="QUESTIONABLE":
        if ramp>=0.97: adj+=7
        elif ramp>=0.90: adj+=3
        elif ramp<=0.82: adj-=3
    adj=int(round(max(2,min(98,adj))))
    return _v696_calibrated_confidence(adj,history,state)


def _v717_trade_guard(offer,target,my_gain,opp_gain):
    """Asset-protection and mutual-benefit gate shared by automatic trade suggestions."""
    if str(target.get("position","")).upper()=="K" or str(offer.get("position","")).upper()=="K":
        return False,"Kicker trade not material"
    give_val=_v690_trade_value(offer); get_val=_v690_trade_value(target); gap=get_val-give_val
    prot=str(_v682_drop_protection(offer) or "").upper()
    if "CORE HOLD" in prot and my_gain<1.50 and gap<1.5:
        return False,"Core asset protection"
    if opp_gain < -0.35:
        return False,"Partner loses too much lineup value"
    if abs(gap)>5.5 and not (my_gain>=1.25 and opp_gain>=0):
        return False,"Asset values too far apart"
    return True,""


def _v717_full_trade_eval(give_df,get_df,my_df,opp_df):
    if give_df.empty or get_df.empty or my_df.empty or opp_df.empty: return None
    mine=_v690_trade_eval(give_df,get_df,my_df)
    if not mine: return None
    opp_before=_v676_roster_score(opp_df)
    opp_after=opp_df[~opp_df["player"].isin(get_df["player"])].copy()
    opp_after=pd.concat([opp_after,give_df],ignore_index=True)
    opp_gain=_v676_roster_score(opp_after)-opp_before
    mine["Partner Gain"]=round(float(opp_gain),2)
    # Stronger verdict requires the trade to be plausible for both managers.
    if float(mine.get("Roster Gain",0))>=1 and opp_gain>=-0.25 and float(mine.get("Net Asset Value",0))>=-1.5:
        mine["Verdict"]="ACCEPT"
    elif float(mine.get("Roster Gain",0))>0.25 and opp_gain>=-0.5 and float(mine.get("Net Asset Value",0))>=-2.0:
        mine["Verdict"]="LEAN ACCEPT"
    else:
        mine["Verdict"]="DECLINE"
    return mine


def _v718_action_queue(board_df,state,history,waiver_df=None,consensus_df=None,trade_ideas=None,limit=5):
    """Only surfaces actions that actually clear the corresponding weekly decision guards."""
    my=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty: return pd.DataFrame()
    actions=[]
    starters,bench,_=_v676_optimize_lineup(my)
    # Availability first.
    for _,sr in starters.iterrows():
        src=my[my["player"].eq(sr.get("Player",""))]
        if src.empty: continue
        r=src.iloc[0]; risk=_v682_injury_risk(r)
        if risk in ("HIGH","UNAVAILABLE","MODERATE"):
            urg=99 if risk=="UNAVAILABLE" else 91 if risk=="HIGH" else 82
            actions.append({"Urgency":urg,"Type":"INJURY","Action":f"{r['player']}: {_v682_injury_action(r)}","Why":f"{_v677_normalize_injury_status(r.get('injury',''))} • {risk}"})
    # Close lineup calls.
    for _,sr in starters.iterrows():
        elig=_v682_eligible_bench(sr,bench)
        if elig is None or elig.empty: continue
        br=elig.sort_values("_start_value",ascending=False).iloc[0]
        gap=float(sr.get("Adjusted PPG",0) or 0)-float(br.get("_start_value",0) or 0)
        if gap<=1.0:
            actions.append({"Urgency":76-int(max(0,gap)*8),"Type":"START/SIT","Action":f"Review {sr['Player']} vs {br['player']}","Why":f"Only {gap:+.2f} projected lineup edge"})
    # Waivers only from the final, already-vetoed waiver table.
    if isinstance(waiver_df,pd.DataFrame) and not waiver_df.empty:
        for _,r in waiver_df.iterrows():
            call=str(r.get("Waiver Call","") or "")
            if "PRIORITY" in call or "ADD NOW" in call:
                actions.append({"Urgency":min(95,int(float(r.get("Priority Score",70) or 70))),"Type":"WAIVER","Action":f"{call}: add {r.get('Add','')}","Why":f"Drop {r.get('Drop','')} • Week {float(r.get('Net Week',0) or 0):+.2f} • ROS {float(r.get('Net ROS',0) or 0):+.2f}"})
    if isinstance(consensus_df,pd.DataFrame) and not consensus_df.empty:
        c=consensus_df[consensus_df["player"].isin(my["player"]) & consensus_df["Consensus Flag"].eq("⚠️ MAJOR DISAGREEMENT")]
        for _,r in c.head(2).iterrows():
            actions.append({"Urgency":66,"Type":"MODEL CHECK","Action":f"Review {r['player']} projection","Why":f"FE vs external {float(r.get('FE vs External',0)):+.2f}"})
    if isinstance(trade_ideas,pd.DataFrame) and not trade_ideas.empty:
        tr=trade_ideas.iloc[0]
        if float(tr.get("Your Gain",0) or 0)>=0.75 and float(tr.get("Partner Gain",0) or 0)>=-0.25:
            actions.append({"Urgency":58,"Type":"TRADE","Action":f"Explore {tr['You Give']} → {tr['You Get']}","Why":f"{tr['Partner']} • you {float(tr['Your Gain']):+.2f}, partner {float(tr['Partner Gain']):+.2f}"})
    if not actions: return pd.DataFrame()
    out=pd.DataFrame(actions).drop_duplicates("Action").sort_values(["Urgency","Type"],ascending=[False,True])
    out["Priority"]=range(1,len(out)+1)
    return out[["Priority","Urgency","Type","Action","Why"]].head(limit)

# ---------------- V6.92 external projection consensus ----------------
@st.cache_data(ttl=1800, show_spinner=False)
def _v692_sleeper_weekly_projections(season,week):
    """Live external weekly projections from Sleeper's projection endpoint."""
    rows=[]
    try:
        url=f"https://api.sleeper.com/projections/nfl/{int(season)}/{int(week)}"
        params={"season_type":"regular","order_by":"pts_ppr"}
        r=requests.get(url,params=params,timeout=10)
        r.raise_for_status()
        data=r.json()
        if not isinstance(data,list):
            return pd.DataFrame()
        for item in data:
            if not isinstance(item,dict):
                continue
            pl=item.get("player") or {}
            stats=item.get("stats") or {}
            name=(
                pl.get("full_name")
                or pl.get("first_name","")+" "+pl.get("last_name","")
                or item.get("player_name")
                or ""
            )
            name=str(name).strip()
            if not name:
                continue
            pos=canonical_position(pl.get("position") or item.get("position") or "")
            team=str(pl.get("team") or item.get("team") or "").upper()
            pts=None
            for key in ["pts_ppr","fantasy_points_ppr","pts_half_ppr","pts_std","points"]:
                if key in stats and stats.get(key) is not None:
                    try:
                        pts=float(stats.get(key))
                        break
                    except Exception:
                        pass
            if pts is None:
                continue
            rows.append({
                "player":name,
                "position":pos,
                "team":team,
                "Sleeper":round(pts,3)
            })
    except Exception:
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()
    out=pd.DataFrame(rows)
    out["_key"]=out["player"].map(_owner_key)
    out=out.sort_values("Sleeper",ascending=False).drop_duplicates("_key")
    return out

@st.cache_data(ttl=1800, show_spinner=False)
def _v692_fantasypros_weekly_projections(season,week,api_key):
    """Optional FantasyPros external projections when the user configures an API key."""
    if not api_key:
        return pd.DataFrame()
    rows=[]
    try:
        url=f"https://api.fantasypros.com/v2/json/nfl/{int(season)}/projections"
        params={
            "week":int(week),
            "positions":"QB:RB:WR:TE:K:DL:DB",
            "scoring":"PPR"
        }
        r=requests.get(
            url,
            params=params,
            headers={"x-api-key":str(api_key)},
            timeout=10
        )
        r.raise_for_status()
        data=r.json()
        players=(data or {}).get("players",[]) if isinstance(data,dict) else []
        for p in players:
            if not isinstance(p,dict):
                continue
            name=str(p.get("name") or "").strip()
            if not name:
                continue
            stats=p.get("stats") or {}
            pts=None
            for key in ["points_ppr","points","fantasy_points"]:
                if stats.get(key) is not None:
                    try:
                        pts=float(stats.get(key))
                        break
                    except Exception:
                        pass
            if pts is None:
                continue
            rows.append({
                "player":name,
                "position":canonical_position(p.get("position_id") or ""),
                "team":str(p.get("team_id") or "").upper(),
                "FantasyPros":round(pts,3)
            })
    except Exception:
        return pd.DataFrame()
    if not rows:
        return pd.DataFrame()
    out=pd.DataFrame(rows)
    out["_key"]=out["player"].map(_owner_key)
    out=out.sort_values("FantasyPros",ascending=False).drop_duplicates("_key")
    return out

def _v692_consensus_table(board_df,season,week,fp_key=""):
    x=board_df.copy()
    x["_key"]=x["player"].map(_owner_key)
    sleeper=_v692_sleeper_weekly_projections(season,week)
    fp=_v692_fantasypros_weekly_projections(season,week,fp_key) if fp_key else pd.DataFrame()

    if not sleeper.empty:
        x=x.merge(sleeper[["_key","Sleeper"]],on="_key",how="left")
    else:
        x["Sleeper"]=np.nan

    if not fp.empty:
        x=x.merge(fp[["_key","FantasyPros"]],on="_key",how="left")
    else:
        x["FantasyPros"]=np.nan

    x["Fantasy Edge"]=pd.to_numeric(x.get("projection",0),errors="coerce").fillna(0.0)
    x["Decision Layer"]=x.apply(_v676_player_value,axis=1)

    ext_cols=[c for c in ["Sleeper","FantasyPros"] if c in x.columns]
    x["External Sources"]=x[ext_cols].notna().sum(axis=1) if ext_cols else 0
    x["External Consensus"]=x[ext_cols].mean(axis=1,skipna=True) if ext_cols else np.nan
    x["FE vs External"]=x["Fantasy Edge"]-x["External Consensus"]
    x["External Spread"]=x[ext_cols].max(axis=1,skipna=True)-x[ext_cols].min(axis=1,skipna=True) if ext_cols else np.nan

    def flag(r):
        n=int(r.get("External Sources",0) or 0)
        d=r.get("FE vs External")
        if n<=0 or pd.isna(d):
            return "NO EXTERNAL MATCH"
        ad=abs(float(d))
        if ad>=3.0:
            return "⚠️ MAJOR DISAGREEMENT"
        if ad>=1.5:
            return "👀 REVIEW"
        return "✅ IN RANGE"
    x["Consensus Flag"]=x.apply(flag,axis=1)
    return x.drop(columns=["_key"],errors="ignore")

# ---------------- V6.93 league-specific scarcity ----------------
def _v693_scarcity_context(board_df,state):
    positions=["QB","RB","WR","TE","DL","DB"]
    rows=[]
    for pos in positions:
        all_pos=board_df[board_df["position"].eq(pos)].copy()
        fa=all_pos[all_pos["player"].map(lambda n:_player_owner(state,n)=="FA")].copy()
        rostered=all_pos[all_pos["player"].map(lambda n:_player_owner(state,n) not in ("FA","ROSTERED_UNKNOWN"))].copy()

        fa["_value"]=fa.apply(_v676_player_value,axis=1) if len(fa) else pd.Series(dtype=float)
        rostered["_value"]=rostered.apply(_v676_player_value,axis=1) if len(rostered) else pd.Series(dtype=float)

        starter_slots={"QB":12,"RB":24,"WR":24,"TE":12,"DL":12,"DB":12}.get(pos,12)
        bench_target={"QB":6,"RB":18,"WR":18,"TE":8,"DL":8,"DB":8}.get(pos,8)
        desired=starter_slots+bench_target

        top_fa=fa.sort_values("_value",ascending=False)
        replacement=float(top_fa.head(max(1,starter_slots//6))["_value"].mean()) if len(top_fa) else 0.0
        quality_threshold=max(3.0,replacement*0.90)
        startable_fa=int((top_fa["_value"]>=quality_threshold).sum()) if len(top_fa) else 0

        rostered_count=len(rostered)
        demand=max(0,desired-rostered_count)
        # Scarcity rises with demand and falls with useful free-agent supply.
        raw=(demand+starter_slots)/(startable_fa+3.0)
        scarcity=max(0.0,min(100.0,20.0+raw*12.0))

        if scarcity>=80: tier="🚨 EXTREME"
        elif scarcity>=65: tier="🔥 HIGH"
        elif scarcity>=50: tier="⚠️ MODERATE"
        else: tier="✅ HEALTHY"

        rows.append({
            "Position":pos,
            "Scarcity Score":round(scarcity,1),
            "Tier":tier,
            "Rostered":rostered_count,
            "Startable FAs":startable_fa,
            "Replacement PPG":round(replacement,2),
            "Demand Gap":demand
        })
    return pd.DataFrame(rows)

def _v693_attach_scarcity(board_df,state):
    out=board_df.copy()
    ctx=_v693_scarcity_context(out,state)
    smap=dict(zip(ctx["Position"],ctx["Scarcity Score"]))
    rmap=dict(zip(ctx["Position"],ctx["Replacement PPG"]))
    out["_scarcity_score"]=out["position"].map(smap).fillna(0.0)
    out["_replacement_ppg"]=out["position"].map(rmap).fillna(0.0)
    out["_scarcity_premium"]=out.apply(
        lambda r:max(0.0,(_v676_player_value(r)-float(r.get("_replacement_ppg",0) or 0)))
                 * (float(r.get("_scarcity_score",0) or 0)/100.0)*0.45,
        axis=1
    )
    return out,ctx

# ---------------- V6.94 automatic trade partner finder ----------------
def _v694_owner_roster(board_df,state,owner):
    return board_df[board_df["player"].map(lambda n:_player_owner(state,n)==str(owner))].copy()

def _v694_position_need(roster_df):
    positions=["QB","RB","WR","TE","DL","DB"]
    if roster_df is None or roster_df.empty:
        return "UNKNOWN"
    vals={}
    minimums={"QB":1,"RB":2,"WR":2,"TE":1,"DL":1,"DB":1}
    for pos in positions:
        sub=roster_df[roster_df["position"].eq(pos)].copy()
        if sub.empty:
            vals[pos]=-999.0
            continue
        sub["_v"]=sub.apply(_v676_player_value,axis=1)
        need_n=minimums[pos]
        vals[pos]=float(sub.nlargest(need_n,"_v")["_v"].sum()) if len(sub)>=need_n else float(sub["_v"].sum())-20
    return min(vals,key=vals.get)

def _v731_team_need_profile(roster_df, board_df):
    """Readable roster need profile used by Trade Intelligence 2.0."""
    minimums={"QB":1,"RB":2,"WR":2,"TE":1,"DL":1,"DB":1}
    labels=[]
    for pos,need_n in minimums.items():
        sub=roster_df[roster_df["position"].eq(pos)].copy()
        if sub.empty:
            labels.append((100.0,pos,f"Needs starting {pos}"))
            continue
        sub["_v731_v"]=sub.apply(_v676_player_value,axis=1)
        vals=sorted(sub["_v731_v"].astype(float).tolist(),reverse=True)
        repl=float(pd.to_numeric(board_df.loc[board_df["position"].eq(pos),"_replacement_ppg"],errors="coerce").dropna().median()) if "_replacement_ppg" in board_df.columns and len(board_df.loc[board_df["position"].eq(pos)]) else 0.0
        if len(vals)<need_n:
            score=90.0+(need_n-len(vals))*5.0
            label=f"Needs starting {pos}"
        else:
            starter=sum(vals[:need_n])/max(1,need_n)
            depth=vals[need_n] if len(vals)>need_n else repl
            starter_margin=starter-repl
            depth_margin=depth-repl
            # Low starter margin is the strongest need; lack of playable depth is secondary.
            score=max(0.0,42.0-starter_margin*4.0)
            if len(vals)<=need_n or depth_margin<1.0:
                score+=12.0
                label=f"Needs {pos} depth" if starter_margin>=2.0 else f"Needs starting {pos}"
            else:
                label=f"Could upgrade {pos}"
        labels.append((score,pos,label))
    labels.sort(reverse=True,key=lambda x:x[0])
    return labels


def _v731_package_label(df):
    return " + ".join(df["player"].astype(str).tolist())


def _v731_trade_package_eval(give_df,get_df,my_df,opp_df):
    """Evaluate a trade by legal optimized lineup, depth, ROS asset value, and both teams' impact."""
    if give_df.empty or get_df.empty or my_df.empty or opp_df.empty:
        return None
    my_before_st,my_before_bench,my_before_lineup=_v676_optimize_lineup(my_df)
    opp_before_st,opp_before_bench,opp_before_lineup=_v676_optimize_lineup(opp_df)
    my_before_score=_v676_roster_score(my_df)
    opp_before_score=_v676_roster_score(opp_df)

    my_after=my_df[~my_df["player"].isin(give_df["player"])].copy()
    my_after=pd.concat([my_after,get_df],ignore_index=True)
    opp_after=opp_df[~opp_df["player"].isin(get_df["player"])].copy()
    opp_after=pd.concat([opp_after,give_df],ignore_index=True)

    _,my_after_bench,my_after_lineup=_v676_optimize_lineup(my_after)
    _,opp_after_bench,opp_after_lineup=_v676_optimize_lineup(opp_after)
    my_after_score=_v676_roster_score(my_after)
    opp_after_score=_v676_roster_score(opp_after)

    give_val=float(give_df.apply(_v690_trade_value,axis=1).sum())
    get_val=float(get_df.apply(_v690_trade_value,axis=1).sum())
    my_ros_before=float(my_df.apply(_v682_ros_value,axis=1).sum())
    my_ros_after=float(my_after.apply(_v682_ros_value,axis=1).sum())
    opp_ros_before=float(opp_df.apply(_v682_ros_value,axis=1).sum())
    opp_ros_after=float(opp_after.apply(_v682_ros_value,axis=1).sum())

    return {
        "my_after":my_after,
        "opp_after":opp_after,
        "My Lineup Gain":float(my_after_lineup-my_before_lineup),
        "Partner Lineup Gain":float(opp_after_lineup-opp_before_lineup),
        "Your Gain":float(my_after_score-my_before_score),
        "Partner Gain":float(opp_after_score-opp_before_score),
        "Asset Gap":float(get_val-give_val),
        "Your ROS %":((my_ros_after-my_ros_before)/my_ros_before*100.0) if my_ros_before>0 else 0.0,
        "Partner ROS %":((opp_ros_after-opp_ros_before)/opp_ros_before*100.0) if opp_ros_before>0 else 0.0,
        "Your Depth Change":float(my_after_bench["_start_value"].head(6).sum()-my_before_bench["_start_value"].head(6).sum()) if len(my_after_bench) or len(my_before_bench) else 0.0,
        "Partner Depth Change":float(opp_after_bench["_start_value"].head(6).sum()-opp_before_bench["_start_value"].head(6).sum()) if len(opp_after_bench) or len(opp_before_bench) else 0.0,
    }


def _v733_trade_recommendation(lineup_gain, your_gain, ros_change, depth_change, partner_gain, trade_fit):
    """Classify a trade by whether it is worth acting on, not merely whether it is fair."""
    lineup_gain=float(lineup_gain or 0)
    your_gain=float(your_gain or 0)
    ros_change=float(ros_change or 0)
    depth_change=float(depth_change or 0)
    partner_gain=float(partner_gain or 0)
    trade_fit=float(trade_fit or 0)

    # Meaningful upgrade with no material long-term sacrifice.
    if lineup_gain >= 1.50 and your_gain >= 1.25 and ros_change >= -0.5 and depth_change >= -2.0 and trade_fit >= 74:
        return "🟢 STRONG SEND", "Meaningful weekly upgrade without a material ROS/depth sacrifice."

    # Big immediate upgrade that costs some future value or depth.
    if lineup_gain >= 2.00 and your_gain >= 1.50 and (ros_change < -0.5 or depth_change < -2.0):
        tradeoff=[]
        if ros_change < -0.5:
            tradeoff.append(f"ROS {ros_change:+.1f}%")
        if depth_change < -2.0:
            tradeoff.append(f"depth {depth_change:+.1f}")
        suffix=", ".join(tradeoff) if tradeoff else "future-value cost"
        return "🟡 AGGRESSIVE UPGRADE", f"Large starting-lineup gain, but you pay a {suffix} trade-off."

    # Technically positive, but too small to justify actively shopping unless user has a specific preference.
    if lineup_gain < 1.00 or your_gain < 0.75:
        return "⚪ MARGINAL", "Positive model result, but the expected improvement is too small to prioritize."

    # Useful but not strong enough for an automatic send recommendation.
    if partner_gain >= -0.25 and trade_fit >= 66:
        return "🟡 CONSIDER", "Helpful roster move, but the edge is not large enough for a strong-send label."

    return "⚪ MARGINAL", "Small or situational improvement; keep as an optional idea rather than a priority move."


def _v694_trade_partner_suggestions(board_df,state,max_rows=20):
    """V7.34 Actionable Trade Recommendations (V7.33 search engine preserved).

    Keeps the V7.31 hard recommendation gates, but uses a cheap first-pass shortlist
    before running the legal-lineup optimizer. This prevents the Trade Finder page
    from blocking while thousands of package permutations are evaluated.
    """
    my=_v694_owner_roster(board_df,state,"1")
    if my.empty:
        return pd.DataFrame()

    my_needs=_v731_team_need_profile(my,board_df)
    my_need_pos,my_need_label=my_needs[0][1],my_needs[0][2]
    suggestions=[]

    my_pool=my[~my["position"].eq("K")].copy()
    my_pool["_tv"]=my_pool.apply(_v690_trade_value,axis=1)
    my_pool["_protected"]=my_pool.apply(lambda r:_v682_drop_protection(r),axis=1)
    # Six movable assets is enough for a useful scan; the manual analyzer remains unrestricted.
    my_pool=my_pool.sort_values("_tv",ascending=False).head(10)

    from itertools import combinations

    for owner in [str(i) for i in range(2,13)]:
        opp=_v694_owner_roster(board_df,state,owner)
        if opp.empty:
            continue
        team_name=state.get("team_names",{}).get(owner,f"Team {owner}")
        opp_needs=_v731_team_need_profile(opp,board_df)
        opp_need_pos,opp_need_label=opp_needs[0][1],opp_needs[0][2]

        opp_pool=opp[~opp["position"].eq("K")].copy()
        opp_pool["_tv"]=opp_pool.apply(_v690_trade_value,axis=1)
        preferred=opp_pool[opp_pool["position"].eq(my_need_pos)].sort_values("_tv",ascending=False).head(4)
        extras=opp_pool.sort_values("_tv",ascending=False).head(4)
        targets=pd.concat([preferred,extras]).drop_duplicates("player").head(6)

        preferred_offers=my_pool[my_pool["position"].eq(opp_need_pos)].sort_values("_tv",ascending=False)
        offer_pool=pd.concat([preferred_offers,my_pool]).drop_duplicates("player").head(7)

        # ----- CHEAP SHORTLIST -----
        # Build candidate packages using only precomputed asset values and need fit.
        # Only the best candidates advance to the expensive legal-lineup evaluation.
        cheap=[]
        single_pkgs=[offer_pool.iloc[[i]] for i in range(len(offer_pool))]
        pair_base=offer_pool.head(5)
        pair_pkgs=[pair_base.iloc[[a,b]] for a,b in combinations(range(len(pair_base)),2)]
        packages=[(x,"1-for-1") for x in single_pkgs] + [(x,"2-for-1") for x in pair_pkgs]

        for _,target in targets.iterrows():
            target_tv=float(target.get("_tv",_v690_trade_value(target)))
            target_need_bonus=2.0 if str(target.get("position",""))==str(my_need_pos) else 0.0
            for give_df,package_type in packages:
                give_tv=float(pd.to_numeric(give_df["_tv"],errors="coerce").fillna(0).sum())
                gap=target_tv-give_tv
                partner_fit=sum(1 for p in give_df["position"].astype(str).tolist() if p==str(opp_need_pos))
                protected=" | ".join(str(x) for x in give_df["_protected"].tolist()).upper()
                if "VERIFIED RESERVE HOLD" in protected:
                    continue
                # Large obvious overpays don't deserve optimizer time unless the target fills our top need.
                if gap < -5.0 and target_need_bonus<=0:
                    continue
                # Prefer near-fair packages, target-need fit and offers that solve partner needs.
                approx = -abs(gap)*0.7 + target_need_bonus + partner_fit*1.5
                if package_type=="2-for-1":
                    approx += 0.6  # small consolidation preference
                cheap.append((approx,target,give_df,package_type))

        cheap.sort(key=lambda x:x[0],reverse=True)
        # Cap expensive optimizer work per opponent. 12 x 11 = at most 132 full evaluations.
        for _,target,give_df,package_type in cheap[:12]:
            get_df=pd.DataFrame([target])
            ev=_v731_trade_package_eval(give_df,get_df,my,opp)
            if not ev:
                continue

            my_gain=float(ev["Your Gain"]); partner_gain=float(ev["Partner Gain"])
            lineup_gain=float(ev["My Lineup Gain"]); asset_gap=float(ev["Asset Gap"])

            # ---- V7.31 HARD RECOMMENDATION GATES (FROZEN) ----
            if my_gain < 0.35:
                continue
            if lineup_gain < 0.15 and my_gain < 0.90:
                continue
            if asset_gap < -2.5 and lineup_gain < 1.75:
                continue
            if partner_gain < -0.50:
                continue

            protected=" | ".join(str(x) for x in give_df["_protected"].tolist()).upper()
            if "CORE HOLD" in protected and lineup_gain < 1.50 and my_gain < 1.75:
                continue
            if "VERIFIED RESERVE HOLD" in protected:
                continue

            fairness=max(0.0,100.0-abs(asset_gap)*7.0-max(0.0,-partner_gain)*22.0)
            improvement=min(100.0,max(0.0,50.0+lineup_gain*14.0+my_gain*8.0))
            mutual=min(100.0,max(0.0,60.0+partner_gain*12.0+float(ev["Partner ROS %"])*1.5))
            fit=max(1.0,min(99.0,0.48*improvement+0.30*fairness+0.22*mutual))

            if fit>=82 and lineup_gain>=0.75:
                grade="A"
            elif fit>=74:
                grade="B+"
            elif fit>=66:
                grade="B"
            else:
                grade="C+"

            give_label=_v731_package_label(give_df)
            get_label=str(target["player"])
            partner_reason=opp_need_label
            your_reason=my_need_label
            if len(give_df)>1:
                trade_type="2-for-1"
                why=f"Consolidate depth into {get_label}; {team_name}: {partner_reason.lower()}"
            else:
                trade_type="1-for-1"
                why=f"{your_reason}; {team_name}: {partner_reason.lower()}"

            recommendation,tradeoff_note=_v733_trade_recommendation(
                lineup_gain,my_gain,float(ev["Your ROS %"]),float(ev["Your Depth Change"]),partner_gain,fit
            )

            suggestions.append({
                "Recommendation":recommendation,
                "Trade Fit":round(fit),
                "Grade":grade,
                "Partner":team_name,
                "Type":trade_type,
                "You Give":give_label,
                "You Get":get_label,
                "Lineup Gain":round(lineup_gain,2),
                "Your Gain":round(my_gain,2),
                "ROS Change":round(float(ev["Your ROS %"]),1),
                "Depth Change":round(float(ev["Your Depth Change"]),2),
                "Partner Gain":round(partner_gain,2),
                "Asset Gap":round(asset_gap,2),
                "Realism":round(fairness),
                "Your Need":your_reason,
                "Their Need":partner_reason,
                "Why":why,
                "Trade-off":tradeoff_note,
            })

    if not suggestions:
        return pd.DataFrame()
    out=pd.DataFrame(suggestions).drop_duplicates(subset=["Partner","You Give","You Get"])
    _tier={"🟢 STRONG SEND":4,"🟡 AGGRESSIVE UPGRADE":3,"🟡 CONSIDER":2,"⚪ MARGINAL":1}
    out["_tier"]=out["Recommendation"].map(_tier).fillna(0)
    out["_rank"]=out["_tier"]*1000.0+out["Lineup Gain"]*3.0+out["Your Gain"]*2.0+out["Trade Fit"]/20.0+out["Partner Gain"]*0.6
    out=out.sort_values(["_rank","Trade Fit","Lineup Gain"],ascending=False).drop(columns=["_rank","_tier"])
    return out.head(max_rows).reset_index(drop=True)

def _v687_consensus_proxy(row):
    core=_v682_num(row,"projection",0); live=_v676_player_value(row); recent=_v682_num(row,"_recent_ppg3",0)
    proxy=live*.6+recent*.4 if recent>0 else live
    diff=core-proxy
    flag="⚠️ MAJOR DISAGREEMENT" if abs(diff)>=3 else "👀 WATCH" if abs(diff)>=1.5 else "OK"
    return round(proxy,2),round(diff,2),flag

def _v688_opportunity_flag(row):
    trend=str(row.get("_role_trend","") or ""); opps=_v682_num(row,"_opps_last",0); delta=_v682_num(row,"_role_delta",0)
    recent=_v682_num(row,"_recent_ppg3",0); proj=_v682_num(row,"projection",0)
    if "RISING" in trend and delta>=3 and opps>=10 and recent<proj*.9: return "🔥 BUY BEFORE BREAKOUT"
    if "RISING" in trend and opps>=8: return "⬆️ ROLE SURGE"
    if "FALLING" in trend and recent>proj: return "⚠️ SELL / FADE"
    return ""

def _v689_team_strength(board_df,state,owner):
    r=board_df[board_df["player"].map(lambda n:_player_owner(state,n)==str(owner))].copy()
    if r.empty: return {"owner":str(owner),"score":0,"weakness":"UNKNOWN","strength":"UNKNOWN","roster":0}
    _,_,lineup=_v676_optimize_lineup(r)
    ps={}
    for p in ["QB","RB","WR","TE","DL","DB"]:
        sub=r[r["position"].eq(p)]
        ps[p]=float(pd.to_numeric(sub["projection"],errors="coerce").fillna(0).sum()) if len(sub) else 0.0
    return {"owner":str(owner),"score":round(float(lineup),2),"weakness":min(ps,key=ps.get),"strength":max(ps,key=ps.get),"roster":len(r)}

def _v690_trade_value(row):
    scarcity=float(row.get("_scarcity_premium",0) or 0)
    return _v682_ros_value(row)+_v676_player_value(row)*.55+scarcity

def _v690_trade_eval(give_df,get_df,my_df):
    if give_df.empty or get_df.empty: return None
    before=_v676_roster_score(my_df)
    after=my_df[~my_df["player"].isin(give_df["player"])].copy()
    after=pd.concat([after,get_df],ignore_index=True)
    aft=_v676_roster_score(after)
    gv=float(give_df.apply(_v690_trade_value,axis=1).sum()); rv=float(get_df.apply(_v690_trade_value,axis=1).sum())
    gain=aft-before; net=rv-gv
    verdict="ACCEPT" if gain>=1 and net>=-1 else "LEAN ACCEPT" if gain>0 and net>=-2 else "DECLINE"
    return {"Before":round(before,2),"After":round(aft,2),"Roster Gain":round(gain,2),"Give Value":round(gv,2),"Get Value":round(rv,2),"Net Asset Value":round(net,2),"Verdict":verdict}

def _v691_top_waiver(board_df,state):
    fa=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="FA")].copy()
    if fa.empty:return None
    fa["_cc_score"]=fa.apply(lambda r:_v682_ros_value(r)+_v676_player_value(r)+max(0,_v683_role_adjustment(r))*2,axis=1)
    return fa.sort_values("_cc_score",ascending=False).iloc[0]

def _v691_roster_weakness(board_df,state):
    my=board_df[board_df["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty:return "UNKNOWN"
    ps={}
    for p in ["QB","RB","WR","TE","DL","DB"]:
        sub=my[my["position"].eq(p)]
        ps[p]=float(pd.to_numeric(sub["projection"],errors="coerce").fillna(0).sum()) if len(sub) else 0
    return min(ps,key=ps.get)

def _v707_apply_live_team_identity(board_df, roster_dir):
    """Identity-only team repair. Never changes projection/VORP/value fields."""
    if board_df is None or board_df.empty or roster_dir is None or roster_dir.empty:
        return board_df
    out=board_df.copy()
    rd=roster_dir.copy()
    rd["_k"]=rd["player"].map(_owner_key)
    team_map=dict(zip(rd["_k"],rd["team"].astype(str).str.upper()))
    out["_v707_k"]=out["player"].map(_owner_key)
    live=out["_v707_k"].map(team_map)
    good=live.notna() & ~live.astype(str).isin(["","FA","NONE","N/A","NFL"])
    out.loc[good,"team"]=live[good]
    out["_live_team_verified"]=good.astype(int)
    return out.drop(columns=["_v707_k"],errors="ignore")

# V7.07: repair current NFL team identity before opponent matching.
try:
    board=_v707_apply_live_team_identity(board,_active_roster_export)
except Exception:
    pass

# V6.78: expensive matchup work happens once per cached refresh, not once per tab.
board,_v678_live_week=_v678_enrich_board_once(board)

# V6.83: role/opportunity is enriched once and shared across weekly tabs.
board=_v683_enrich_role(board,_v678_live_week.get("season",datetime.now().year))
_v683_health=_v683_data_health(
    board,
    _v678_live_week.get("season",datetime.now().year),
    _v678_live_week.get("week",1)
)

# V6.93: league-specific scarcity is attached once and shared by waiver/trade views.
board,_v693_scarcity=_v693_attach_scarcity(board,state)
# V7.07: attach live external weekly projection as evidence/context only.
try:
    _v707_wp=_v692_sleeper_weekly_projections(
        int(_v678_live_week.get("season",datetime.now().year)),
        int(_v678_live_week.get("week",1))
    )
    board["_v707_key"]=board["player"].map(_owner_key)
    if isinstance(_v707_wp,pd.DataFrame) and len(_v707_wp):
        board=board.merge(_v707_wp[["_key","Sleeper"]].rename(columns={"Sleeper":"_external_week_projection"}),left_on="_v707_key",right_on="_key",how="left")
        board.drop(columns=["_key"],inplace=True,errors="ignore")
    else:
        board["_external_week_projection"]=np.nan
    board.drop(columns=["_v707_key"],inplace=True,errors="ignore")
except Exception:
    board["_external_week_projection"]=np.nan

# V7.44 IMPORTANT: V7.43 calculated role confidence before external projections were
# attached, so the strongest pregame signal could never contribute. Recompute confidence
# after the external merge while leaving observed usage fields untouched.
try:
    _v744_rc=board.apply(_v743_role_confidence,axis=1)
    board["_role_confidence"]=[x[0] for x in _v744_rc]
    board["_role_confidence_source"]=[x[1] for x in _v744_rc]
except Exception:
    pass


try:
    _v695_saved,_v695_saved_key=_v695_autosave_snapshot(
        board,state,int(_v678_live_week.get("season",datetime.now().year)),
        int(_v678_live_week.get("week",1)),globals().get("_best",pd.DataFrame())
    )
except Exception:
    _v695_saved,_v695_saved_key=False,None

tabs=st.tabs(["⚙️ League Setup","🎯 Draft Mode","🧪 Mock Draft Lab","🧲 Waiver Priority","🛡️ IDP Board","📈 Breakout / Regression","🏁 Start / Sit","🔎 Player Lab","📊 Accuracy + Calibration","🧠 IDP Intelligence","📡 External Consensus","🚨 Opportunity Detector","🕵️ League Scarcity","🔁 Trade Finder","🏠 Action Queue"])
# V7.19 adds named Start/Sit alternatives, no-fake-edge handling, close-decision cards, and IDP external-consensus validity guards on top of V7.18.

def _snake_owner(overall_pick, teams):
    rnd=max(1,(int(overall_pick)-1)//int(teams)+1)
    within=(int(overall_pick)-1)%int(teams)+1
    return within if rnd%2==1 else int(teams)-within+1


def _sim_opponent_pick_fast(avail, opp_counts, rnd, randomness, rng):
    """Fast opponent simulation; user picks still use the full Fantasy Edge engine."""
    if avail.empty:
        return None

    # Opponents do not need the expensive Fantasy Edge candidate pipeline.
    # Restrict to the market-relevant front of the board plus any required IDP/K candidates.
    fallback=_safe_num_series(avail,"model_rank",999.0)
    if "consensus_rank" in avail.columns:
        market=pd.to_numeric(avail["consensus_rank"],errors="coerce").fillna(fallback)
    else:
        market=fallback.copy()

    # Most realistic opponent choices come from the top market band.
    front_idx=market.nsmallest(min(90,len(avail))).index
    need_pos=[]
    if rnd>=9 and int(opp_counts.get("DL",0))<1: need_pos.append("DL")
    if rnd>=10 and int(opp_counts.get("DB",0))<1: need_pos.append("DB")
    if rnd>=14 and int(opp_counts.get("K",0))<1: need_pos.append("K")
    extra_idx=avail.index[avail.position.isin(need_pos)] if need_pos else pd.Index([])
    idx=front_idx.union(extra_idx)
    a=avail.loc[idx].copy()

    # Preserve a minimal league-wide tail at scarce required positions. This does
    # not reserve a named player for the user; it prevents the lightweight
    # opponent model from unrealistically vacuuming an entire required position.
    # The packaged certification board is compact, so preserve a realistic
    # replacement-level tail that would exist in the actual Yahoo room.
    # These are NOT reserved named targets; they simply prevent the lightweight
    # opponent model from consuming the entire position universe.
    _scarce_floor={"QB":2,"RB":6,"WR":8,"TE":2,"K":2,"DL":2,"DB":2}
    for _p,_floor in _scarce_floor.items():
        _remaining=int((avail["position"].astype(str)==_p).sum())
        if _remaining<=_floor:
            a=a[~a["position"].astype(str).eq(_p)].copy()
    if a.empty:
        a=avail.loc[front_idx].copy()

    _amodel=_safe_num_series(a,"model_rank",999.0)
    if "consensus_rank" in a.columns:
        base=pd.to_numeric(a["consensus_rank"],errors="coerce").fillna(_amodel)
    else:
        base=_amodel
    score=base.to_numpy(dtype=float)+rng.normal(0,max(float(randomness),1.0),len(a))
    pos=a["position"].astype(str).to_numpy()

    # Vectorized roster-needs adjustments.
    if rnd<=7:
        score += np.where(np.isin(pos,["DL","DB"]),25.0,0.0)
    if rnd>=9 and int(opp_counts.get("DL",0))<1:
        score += np.where(pos=="DL",-7.0,0.0)
    if rnd>=10 and int(opp_counts.get("DB",0))<1:
        score += np.where(pos=="DB",-7.0,0.0)
    if rnd>=14 and int(opp_counts.get("K",0))<1:
        score += np.where(pos=="K",-8.0,0.0)

    if int(opp_counts.get("QB",0))>=1: score += np.where(pos=="QB",12.0,0.0)
    if int(opp_counts.get("TE",0))>=1: score += np.where(pos=="TE",8.0,0.0)
    if int(opp_counts.get("K",0))>=1: score += np.where(pos=="K",100.0,0.0)
    if int(opp_counts.get("DL",0))>=1: score += np.where(pos=="DL",5.0,0.0)
    if int(opp_counts.get("DB",0))>=1: score += np.where(pos=="DB",5.0,0.0)

    return a.iloc[int(np.argmin(score))]




@st.cache_data(show_spinner=False)
def _prepare_fast_sim_board(board):
    """
    Precompute IDP evidence once for automated simulations.
    This keeps the 100-draft test fast while avoiding neutral/missing IDP defaults.
    """
    y=board.copy()
    if "position" not in y.columns and "Position" in y.columns:
        y["position"]=y["Position"].map(canonical_position)
    if "player" not in y.columns and "Player" in y.columns:
        y["player"]=y["Player"].astype(str)

    # Align certified-board names where necessary.
    alias_pairs={
        "projection":["projection","proj","fantasy_points","projected_points"],
        "vorp":["vorp","VORP","v9_vorp"],
        "model_rank":["model_rank","Model_rank","v9_model_rank"],
        "consensus_rank":["consensus_rank","market_pick","Market_pick","v9_market_pick"],
        "market_pick":["market_pick","Market_pick","consensus_rank","v9_market_pick"],
    }
    for target,candidates in alias_pairs.items():
        if target not in y.columns:
            for c in candidates:
                if c in y.columns:
                    y[target]=y[c]
                    break

    y["idp_external_rank"]=np.nan
    y["idp_impact_score"]=np.nan
    y["idp_quality_tier"]=np.nan
    y["idp_eligible"]=False

    mask=y["position"].astype(str).str.upper().isin(["DL","DB"])
    if mask.any():
        rows=y.loc[mask].copy()
        y.loc[mask,"idp_external_rank"]=rows.apply(_v936_external_idp_rank,axis=1)

        impact=rows.apply(_v935_idp_impact_score,axis=1)
        y.loc[mask,"idp_impact_score"]=[v[0] for v in impact]
        y.loc[mask,"idp_eligible"]=[bool(v[1]) for v in impact]

        quality=rows.apply(_v941_idp_quality,axis=1)
        y.loc[mask,"idp_quality_tier"]=[v[0] for v in quality]

        # Consensus-backed fallback used by production scoring for strong known IDPs.
        er=pd.to_numeric(y.loc[mask,"idp_external_rank"],errors="coerce")
        pos=y.loc[mask,"position"].astype(str)
        fallback=((pos.eq("DL") & er.notna() & (er<=15)) |
                  (pos.eq("DB") & er.notna() & (er<=20)))
        if fallback.any():
            idx=fallback.index[fallback]
            y.loc[idx,"idp_eligible"]=True
            floor=np.where(
                y.loc[idx,"position"].eq("DL"),
                np.maximum(5.5,16.0-pd.to_numeric(y.loc[idx,"idp_external_rank"],errors="coerce")*0.60),
                np.maximum(5.0,14.0-pd.to_numeric(y.loc[idx,"idp_external_rank"],errors="coerce")*0.42)
            )
            current=pd.to_numeric(y.loc[idx,"idp_impact_score"],errors="coerce").fillna(0.0)
            y.loc[idx,"idp_impact_score"]=np.maximum(current.to_numpy(),floor)

    y["_sim_precomputed_idp"]=True
    return y


def _fast_sim_user_pick(avail, roster_rows, rnd, overall, slot, teams, slots, randomness, rng):
    """
    Simulation-only scorer that mirrors current Fantasy Edge decision principles.
    Optional numeric columns are always expanded to index-aligned Series.
    Live Draft and Interactive Mock remain unchanged.
    """
    if avail.empty:
        return None

    a=avail.copy()

    def _num_col(name, default=0.0):
        if name in a.columns:
            return pd.to_numeric(a[name],errors="coerce").fillna(float(default))
        return pd.Series(float(default),index=a.index,dtype=float)

    counts={}
    if roster_rows:
        for rr in roster_rows:
            p=str(rr.get("position",""))
            counts[p]=counts.get(p,0)+1

    proj=_num_col("projection",0.0)
    vorp=_num_col("vorp",0.0)
    model_rank=_num_col("model_rank",999.0)
    if "consensus_rank" in a.columns:
        market=pd.to_numeric(a["consensus_rank"],errors="coerce").fillna(model_rank)
    else:
        market=model_rank.copy()

    score=(proj*0.85)+(vorp*3.2)-np.minimum(market,300)*0.025
    pos=a["position"].astype(str)

    rounds=int(sum(int(v) for k,v in slots.items() if k!="FLEX") + int(slots.get("FLEX",0)))
    remaining_after=max(rounds-int(rnd),0)

    def min_required(after):
        fixed={p:max(int(slots.get(p,0))-int(after.get(p,0)),0)
               for p in ["QB","RB","WR","TE","K","DL","DB"]}
        required_skill=(
            int(slots.get("RB",0))+int(slots.get("WR",0))+
            int(slots.get("TE",0))+int(slots.get("FLEX",0))
        )
        have_skill=int(after.get("RB",0))+int(after.get("WR",0))+int(after.get("TE",0))
        fixed_skill=fixed["RB"]+fixed["WR"]+fixed["TE"]
        flex_extra=max(required_skill-have_skill-fixed_skill,0)
        return int(sum(fixed.values())+flex_extra)

    feasible=np.ones(len(a),dtype=bool)
    for p in ["QB","RB","WR","TE","K","DL","DB"]:
        idx=np.where(pos.to_numpy()==p)[0]
        if len(idx):
            after=dict(counts)
            after[p]=after.get(p,0)+1
            if min_required(after)>remaining_after:
                feasible[idx]=False

    rb=counts.get("RB",0); wr=counts.get("WR",0); te=counts.get("TE",0)
    qb=counts.get("QB",0); dl=counts.get("DL",0); db=counts.get("DB",0); k=counts.get("K",0)

    score += np.where((pos=="WR") & (wr<2),7.0,0.0)
    score += np.where((pos=="TE") & (te<1) & (rnd>=4),2.5,0.0)

    if rb>=2 and rnd<=6: score += np.where(pos=="RB",-3.0,0.0)
    if rb>=3 and rnd<=7: score += np.where(pos=="RB",-8.0,0.0)
    if rb>=4: score += np.where(pos=="RB",-5.5,0.0)
    if rb>=5: score += np.where(pos=="RB",-22.0,0.0)

    if wr>=5: score += np.where(pos=="WR",-8.0,0.0)
    if qb>=1: score += np.where(pos=="QB",-12.0,0.0)
    if te>=1: score += np.where(pos=="TE",-9.0,0.0)
    if k>=1: feasible &= (pos!="K").to_numpy()

    if dl>=1 and db<1:
        score += np.where(pos=="DB",14.0,0.0)
        score += np.where(pos=="DL",-20.0,0.0)
    if db>=1 and dl<1:
        score += np.where(pos=="DL",14.0,0.0)
        score += np.where(pos=="DB",-20.0,0.0)

    idp=pos.isin(["DL","DB"])
    tier=_num_col("idp_quality_tier",5.0)
    impact=_num_col("idp_impact_score",0.0)
    talent=_num_col("idp_talent_score",0.0)
    idp_ropp=_num_col("roster_opportunity_adj",0.0)

    impact_idp=idp & (tier<=2) & (idp_ropp>=-5.0)
    score += np.where(impact_idp,0.20*impact+0.16*talent+5.0,0.0)

    total_idp=dl+db

    # Controlled marginal-value IDP portfolio.
    # Required DL/DB are protected. A third impact defender is optional and must
    # clearly beat redundant bench offense. A fourth defender is not drafted.
    if dl>=1 and db>=1:
        if total_idp>=3:
            feasible &= (~idp).to_numpy()
        elif rnd>=11 and impact_idp.any():
            best_idp=float(np.nanmax(np.where(impact_idp,score,-1e9)))
            deep_offense=(
                ((pos=="RB") & (rb>=3)) |
                ((pos=="WR") & (wr>=3)) |
                ((pos=="QB") & (qb>=1)) |
                ((pos=="TE") & (te>=1))
            )
            best_off=float(np.nanmax(np.where(deep_offense,score,-1e9))) if deep_offense.any() else -1e9
            required_edge=6.5+rng.normal(0,2.0)
            if best_idp <= best_off+required_edge:
                feasible &= (~idp).to_numpy()

        feasible &= (~(idp & ((tier>2) | (idp_ropp<-5.0)))).to_numpy()

    true_reach=np.maximum(market-float(overall),0.0)
    faller=np.maximum(float(overall)-market,0.0)
    score -= np.minimum(true_reach,40.0)*0.20
    score += np.minimum(faller,48.0)*0.02

    score += rng.normal(0,max(float(randomness),1.0)*0.10,len(a))
    score=np.where(feasible,score,-1e9)

    if not np.isfinite(score).any():
        return None
    return a.iloc[int(np.nanargmax(score))]




def _sim_user_pick_same_engine(avail,roster,round_no,current_pick,slot,teams,slots,randomness=6):
    """Automated user picks use the exact Live/Interactive-Mock preparation pipeline."""
    # V6.11 Merit Depth Champion: certification uses the exact same currently
    # available player pool as Live Draft / Interactive Mock. Do not let a
    # benchmark-only prefilter choose the champion.
    sim_avail=avail.copy()
    ranked,next_pick=prepare_user_draft_candidates(
        sim_avail,roster.copy(),int(round_no),int(current_pick),
        int(slot),int(teams),slots,int(randomness)
    )

    # The benchmark prefilter is only a speed optimization. If it accidentally
    # removes every legal completion candidate, retry the exact production
    # pipeline on the full currently available pool.
    if ranked is None or len(ranked)==0:
        ranked,next_pick=prepare_user_draft_candidates(
            avail.copy(),roster.copy(),int(round_no),int(current_pick),
            int(slot),int(teams),slots,int(randomness)
        )

    if ranked is None or len(ranked)==0:
        counts=roster.position.value_counts().to_dict() if roster is not None and len(roster) else {}
        remaining={p:int((avail["position"].astype(str)==p).sum()) for p in ["QB","RB","WR","TE","K","DL","DB"]}
        minimum_now,fixed_def,flex_extra=_minimum_required_picks_remaining(counts,slots)

        # Benchmark-only compact-pool recovery. In a real Yahoo room, RB/WR depth
        # extends well beyond the certified board. If the benchmark's compact pool
        # has exhausted both RB and WR after all requirements are complete, choose
        # the best remaining non-K/non-extra-IDP depth player rather than crash.
        if minimum_now==0 and remaining.get("RB",0)==0 and remaining.get("WR",0)==0:
            recovery=avail.copy()
            # Never create K2 or a fourth IDP in recovery.
            if int(counts.get("K",0))>=1:
                recovery=recovery[recovery["position"].astype(str)!="K"]
            _idp_total=int(counts.get("DL",0))+int(counts.get("DB",0))
            if _idp_total>=3:
                recovery=recovery[~recovery["position"].astype(str).isin(["DL","DB"])]

            # Prefer TE3 over QB3 if those are the only realistic compact-board
            # depth options; rank by the same production value fields.
            if len(recovery):
                recovery=recovery.copy()
                recovery["_recovery_score"]=(
                    _safe_num_series(recovery,"draft_score",0.0) +
                    1.5*_safe_num_series(recovery,"vorp",0.0) +
                    0.25*_safe_num_series(recovery,"projection",0.0)
                )
                _te=recovery[recovery["position"].astype(str).eq("TE")]
                _qb=recovery[recovery["position"].astype(str).eq("QB")]
                if len(_te):
                    return _te.sort_values("_recovery_score",ascending=False).iloc[0]
                if len(_qb):
                    return _qb.sort_values("_recovery_score",ascending=False).iloc[0]

        raise RuntimeError(
            f"No eligible production candidate | round={int(round_no)} overall={int(current_pick)} "
            f"roster={counts} missing_fixed={fixed_def} flex_extra={flex_extra} "
            f"minimum_required={minimum_now} requirements_complete={minimum_now==0} remaining_pool={remaining}"
        )
    return ranked.iloc[0]



def simulate_current_fantasy_edge_once(board, teams, slot, rounds, slots, randomness, seed):
    """Fast simulation: exact Fantasy Edge logic for user picks + lightweight realistic opponents."""
    rng=np.random.default_rng(int(seed))

    # Certification counters MUST exist before the first simulated user pick.
    production_engine_user_picks=0
    user_pick_count=0
    unavailable_user_picks=0

    # Build availability once, then drop one selected row per pick.
    avail=board.copy()
    if "_sim_key" not in avail.columns:
        avail["_sim_key"]=np.arange(len(avail),dtype=int)
    avail=avail.set_index("_sim_key",drop=False)

    user_rows=[]
    opp_counts={i:{} for i in range(1,int(teams)+1)}

    for overall in range(1,int(teams)*int(rounds)+1):
        if avail.empty:
            break
        rnd=max(1,(overall-1)//int(teams)+1)
        owner=_snake_owner(overall,int(teams))

        if int(owner)==int(slot):
            roster=pd.DataFrame(user_rows) if user_rows else board.iloc[0:0].copy()

            # Ultra-fast simulation scorer mirrors the current Fantasy Edge principles.
            # Live Draft + Interactive Mock still use the exact full production engine.
            choice=_sim_user_pick_same_engine(
                avail.reset_index(drop=True),roster,int(rnd),int(overall),
                int(slot),int(teams),slots,int(randomness)
            )
            production_engine_user_picks+=1
            user_pick_count+=1

            if choice is None:
                continue
            choice=choice.copy()

            _choice_name=str(choice.get("player",""))
            if _choice_name not in set(avail["player"].astype(str)):
                unavailable_user_picks+=1
                raise RuntimeError(f"Production engine recommended unavailable player: {_choice_name}")
            row=choice.to_dict()
            row["mock_round"]=rnd
            row["mock_pick"]=overall
            user_rows.append(row)

            # Drop by unique player key rather than rebuilding availability from board.
            pname=str(choice.player)
            hit=avail.index[avail.player.astype(str).eq(pname)]
            if len(hit):
                avail=avail.drop(hit[0])

        else:
            oc=opp_counts.setdefault(int(owner),{})
            choice=_sim_opponent_pick_fast(avail,oc,rnd,randomness,rng)
            if choice is not None:
                p=str(choice.position)
                oc[p]=int(oc.get(p,0))+1
                avail=avail.drop(choice.name)

    roster=pd.DataFrame(user_rows)
    if roster.empty:
        return None

    g=grade_mock(roster,int(teams),slots)
    c=roster.position.value_counts().to_dict()
    required_ok=all([
        c.get("QB",0)>=int(slots.get("QB",1)),
        c.get("RB",0)>=int(slots.get("RB",2)),
        c.get("WR",0)>=int(slots.get("WR",2)),
        c.get("TE",0)>=int(slots.get("TE",1)),
        c.get("K",0)>=int(slots.get("K",1)),
        c.get("DL",0)>=int(slots.get("DL",1)),
        c.get("DB",0)>=int(slots.get("DB",1)),
    ])

    _audit=_v610_roster_regret_audit(roster,slots)
    _result={
        "grade":float(g.get("score",np.nan)),
        "model_edge":float(g.get("model_edge_score",np.nan)),
        "draft_value":float(g.get("draft_value",np.nan)),
        "raw_market_draft_value":float(g.get("raw_market_draft_value",g.get("draft_value",np.nan))),
        "construction":float(g.get("construction",np.nan)),
        "positional_advantage":float(g.get("positional_advantage",np.nan)),
        "opportunity_penalty":float(g.get("opportunity_penalty",np.nan)),
        "raw_opportunity_penalty":float(g.get("raw_opportunity_penalty",g.get("opportunity_penalty",np.nan))),
        "RB":int(c.get("RB",0)),"WR":int(c.get("WR",0)),
        "QB":int(c.get("QB",0)),"TE":int(c.get("TE",0)),
        "K":int(c.get("K",0)),"DL":int(c.get("DL",0)),"DB":int(c.get("DB",0)),
        "IDP_total":int(c.get("DL",0))+int(c.get("DB",0)),
        "extra_IDP":max(int(c.get("DL",0))+int(c.get("DB",0))-2,0),
        "legal_roster":bool(required_ok),
        "production_engine_user_picks":int(production_engine_user_picks),
        "user_pick_count":int(user_pick_count),
        "production_engine_usage":float(production_engine_user_picks/max(user_pick_count,1)),
        "unavailable_user_picks":int(unavailable_user_picks),
        "duplicate_user_players":int(len(roster["player"])-roster["player"].nunique()) if "player" in roster.columns else 0,
        "roster_size":int(len(roster)),
        "expected_roster_size":int(exact_roster_rounds(slots)),
        "certified_expected_roster":bool(len(roster)==int(exact_roster_rounds(slots))),
        "starter_vorp":float(_audit["starter_vorp"]),
        "bench_upside":float(_audit["bench_upside"]),
        "harmful_regret_count":int(_audit["harmful_regret_count"]),
        "major_reach_count":int(_audit["major_reach_count"]),
        "raw_major_reach_count":int(_audit.get("raw_major_reach_count",_audit["major_reach_count"])),
        "early_backup_count":int(_audit["early_backup_count"]),
        "drafted_players":" | ".join([f"{int(rr.get('mock_pick',0))}:{rr.get('player','')}({rr.get('position','')},mkt={rr.get('consensus_rank','')})" for rr in user_rows]),
    }
    _result["champion_score"]=_v610_champion_score(_result)
    return _result


with tabs[0]:
    st.subheader("League Ownership & Roster Recovery")
    st.caption("Rebuild each roster once. Waiver Wire now uses this ownership map, so only true free agents appear.")
    _cloud_ok=st.session_state.get("_v657_cloud_ok",False)
    _cloud_mode=st.session_state.get("_v705_cloud_mode",_v705_prior.get("mode","UNKNOWN"))
    _cloud_checked=st.session_state.get("_v705_cloud_checked_at",_v705_prior.get("checked_at",""))
    _cloud_updated=st.session_state.get("_v705_cloud_updated_at",_v705_prior.get("cloud_updated_at",""))
    _local_stats=_v705_ownership_stats(state)

    if _cloud_ok:
        if _cloud_mode=="LOCAL_PROTECTED_AND_REPAIRED":
            st.success("🛡️ Cloud sync verified. A less-complete cloud copy was blocked and repaired from this local league.")
        else:
            st.success("☁️ Cloud sync connected and verified.")
    else:
        st.warning("☁️ Cloud unavailable/unverified — protected local mode is active. Your local league state will not be overwritten.")

    _sc1,_sc2,_sc3,_sc4=st.columns(4)
    _sc1.metric("Sync mode",str(_cloud_mode).replace("_"," ").title())
    _sc2.metric("Protected rostered",_local_stats["rostered"])
    _sc3.metric("Unknown teams",_local_stats["unknown"])
    _sc4.metric("Integrity guard","ON")
    if _cloud_checked:
        st.caption(f"Last cloud check: {_cloud_checked}" + (f" • Cloud row updated: {_cloud_updated}" if _cloud_updated else ""))

    _tc1,_tc2=st.columns([1,3])
    with _tc1:
        if st.button("☁️ Test Cloud Sync",key="v705_test_cloud"):
            try:
                _testrow=_cloud_probe()
                if not isinstance(_testrow,dict) or not isinstance(_testrow.get("state"),dict):
                    raise RuntimeError("Connected, but no league state row was returned.")
                _teststate=_testrow["state"]
                _sus,_reason=_v705_state_is_suspicious(_teststate,state)
                if _sus:
                    _v705_write_sync_status(False,"PROTECTED_CONFLICT",_reason,_testrow.get("updated_at",""))
                    st.error(f"Cloud connection works, but sync was blocked: {_reason}")
                else:
                    _v705_write_sync_status(True,"CONNECTED_VERIFIED","",_testrow.get("updated_at",""))
                    st.success("Cloud read test passed. Local ownership is protected and the cloud copy is compatible.")
            except Exception as _e:
                _v705_write_sync_status(False,"LOCAL_ONLY",repr(_e),"")
                st.error(f"Cloud test failed. Staying safely local: {_e}")
    with _tc2:
        st.caption("The test is read-only. It will not overwrite your local or cloud roster.")

    if st.session_state.get("_v657_cloud_error"):
        with st.expander("Cloud sync diagnostic details"):
            st.code(st.session_state.get("_v657_cloud_error"))


    with st.expander("✏️ Rename league teams",expanded=False):
        _new_names={}
        _cols=st.columns(3)
        for i in range(1,int(teams)+1):
            with _cols[(i-1)%3]:
                _new_names[str(i)]=st.text_input(f"Team {i} name",value=state["team_names"].get(str(i),"My Team" if i==1 else f"Team {i}"),key=f"v656_name_{i}")
        if st.button("Save team names",key="v656_names_save"):
            state["team_names"].update(_new_names); save_state(state); st.success("Team names saved.")

    def _owner_label(o):
        if o=="FA": return "Free Agent"
        if o=="ROSTERED_UNKNOWN": return "Rostered — team unknown"
        return state["team_names"].get(str(o),f"Team {o}")

    c1,c2,c3=st.columns([2,2,1])
    with c1:
        _move_player=st.selectbox("Player",[""]+sorted(all_names),key="v656_move_player")
    _owner_options=["FA","ROSTERED_UNKNOWN"]+[str(i) for i in range(1,int(teams)+1)]
    with c2:
        _cur=_player_owner(state,_move_player) if _move_player else "FA"
        _idx=_owner_options.index(_cur) if _cur in _owner_options else 0
        _move_owner=st.selectbox("Move to",_owner_options,index=_idx,format_func=_owner_label,key="v656_move_owner")
    with c3:
        st.write(""); st.write("")
        if st.button("Move",use_container_width=True,disabled=not bool(_move_player),key="v656_move"):
            k=_owner_key(_move_player)
            if _move_owner=="FA": state["ownership"].pop(k,None)
            else: state["ownership"][k]={"player":_move_player,"owner":_move_owner}
            _sync_legacy_from_ownership(state); save_state(state); st.rerun()

    _team=st.selectbox("Edit full roster",[str(i) for i in range(1,int(teams)+1)],format_func=lambda o:state["team_names"].get(o,f"Team {o}"),key="v656_team")
    _current=[r.get("player") for r in state["ownership"].values() if isinstance(r,dict) and str(r.get("owner"))==_team and r.get("player")]
    _opts=list(dict.fromkeys(all_names+_current))
    _edited=st.multiselect(f"Players on {state['team_names'].get(_team,'Team '+_team)}",_opts,default=[p for p in _current if p in set(_opts)],key=f"v656_roster_{_team}")
    if st.button("💾 Save this team roster",key="v656_save_roster"):
        for k,r in list(state["ownership"].items()):
            if isinstance(r,dict) and str(r.get("owner"))==_team: state["ownership"].pop(k,None)
        for p in _edited: state["ownership"][_owner_key(p)]={"player":p,"owner":_team}
        _sync_legacy_from_ownership(state); save_state(state); st.rerun()

    _unknown=[r.get("player") for r in state["ownership"].values() if isinstance(r,dict) and r.get("owner")=="ROSTERED_UNKNOWN"]
    a,b,c=st.columns(3)
    a.metric("Rostered",sum(1 for r in state["ownership"].values() if isinstance(r,dict) and r.get("owner")!="FA"))
    b.metric("Team unknown",len(_unknown))
    c.metric("Free agents",sum(1 for n in all_names if _is_free_agent(state,n)))

    # V7.01 ownership integrity audit across raw names and persisted sources.
    _audit_rows=[]
    _alias_groups={}
    for _n in all_names:
        _alias_groups.setdefault(_owner_key(_n),[]).append(str(_n))
    for _key,_variants in _alias_groups.items():
        _variants=sorted(set(_variants))
        if len(_variants)>1:
            _audit_rows.append({"Issue":"Duplicate identity","Player / Key":_key,"Details":" | ".join(_variants)})
    _own=state.get("ownership",{}) or {}
    for _n in list(state.get("taken",[]) or [])+[
        e.get("player","") for e in (state.get("draft_log",[]) or []) if isinstance(e,dict)
    ]:
        _key=_owner_key(_n); _rec=_own.get(_key)
        if _key and (not isinstance(_rec,dict) or str(_rec.get("owner","FA"))=="FA"):
            _audit_rows.append({"Issue":"Drafted but marked available","Player / Key":str(_n),"Details":"Blocked by hard availability guard"})
    for _entry in (state.get("draft_log",[]) or []):
        if not isinstance(_entry,dict): continue
        _n=str(_entry.get("player","") or ""); _rec=_own.get(_owner_key(_n))
        if not _n or not isinstance(_rec,dict): continue
        _logged_mine=str(_entry.get("owner","")).strip().lower()=="mine"
        _mapped_mine=str(_rec.get("owner",""))=="1"
        if _logged_mine!=_mapped_mine:
            _audit_rows.append({"Issue":"Conflicting owner","Player / Key":_n,"Details":"Draft log and ownership map disagree"})
    _audit_df=pd.DataFrame(_audit_rows).drop_duplicates() if _audit_rows else pd.DataFrame()
    with st.expander(f"🧾 Ownership integrity audit ({len(_audit_df)} flags)",expanded=bool(len(_audit_df))):
        if _audit_df.empty: st.success("No duplicate identities, ownership conflicts, or drafted-as-available players found.")
        else: st.dataframe(_audit_df,use_container_width=True,hide_index=True)
    if _unknown:
        with st.expander(f"⚠️ Assign {len(_unknown)} historical picks to opponent teams",expanded=False):
            st.write(", ".join(sorted(_unknown)))

    st.download_button("⬇️ Backup complete league state",json.dumps(state,indent=2),file_name="fantasy_edge_league_state.json",mime="application/json")
    restore=st.file_uploader("Restore league backup",type=["json"],key="v656_restore")
    if restore and st.button("Restore backup",key="v656_restore_btn"):
        STATE.write_bytes(restore.getvalue()); st.success("Restored. Refresh the page.")

with tabs[1]:
    st.subheader("Live Draft Assistant")
    st.success("✅ Live and Mock use the same player pool, eligibility, roster construction, injury rules, timing, and recommendation engine.")
    _pool_check_names=set(board["player"].astype(str))
    _pool_check=["CeeDee Lamb","Kenneth Walker III","DeVonta Smith","Bo Nix","Colston Loveland","Ladd McConkey","David Montgomery","Bhayshul Tuten","Jeremiyah Love","Jadarian Price","Carnell Tate","George Kittle","Harold Fannin Jr.","Dalton Kincaid","Isaiah Likely","KC Concepcion","Jayden Reed","Matthew Golden","Jayden Higgins","Kenyon Sadiq","DJ Moore","Luther Burden III"]
    st.caption("Player-pool check: "+", ".join([f"{_n} ✓" if _n in _pool_check_names else f"{_n} MISSING" for _n in _pool_check]))
    if len(_active_roster_export):
        _export_cols=[c for c in ["player_id","player","position","raw_position","team","active","injury_status","years_exp","external_ecr_rank"] if c in _active_roster_export.columns]
        st.download_button(
            "⬇️ Export active NFL roster CSV",
            _active_roster_export[_export_cols].to_csv(index=False).encode("utf-8"),
            file_name="FantasyEdge_2026_Active_NFL_Roster.csv",
            mime="text/csv",
            key="v633_active_roster_export"
        )
        _depth_added=int((board.get("pool_status",pd.Series(index=board.index,dtype=str)).astype(str)=="DEPTH_ONLY").sum())
        st.caption(f"Active roster added {_depth_added} missing NFL players to the Live Draft dropdown. Ranked recommendations remain protected from placeholder-only players.")
    live_slot=st.number_input("Your Yahoo draft slot (for pick-timing estimates)",1,int(teams),min(int(state.get("mock",{}).get("draft_slot",1)),int(teams)),key="v761_live_slot")

    with st.expander("🚑 Live Injury Center", expanded=False):
        _v681_watch_now=_v680_injury_watch_feed()
        _v681_q=sum(1 for v in _v681_watch_now.values() if _v677_normalize_injury_status(v.get("status","ACTIVE"))=="QUESTIONABLE")
        _v681_reserve=sum(1 for v in _v681_watch_now.values() if _v677_normalize_injury_status(v.get("status","ACTIVE")) in ("IR","PUP","NFI","SUSPENDED"))
        _v681_practice=sum(1 for v in _v681_watch_now.values() if str(v.get("practice","") or "").strip())
        st.caption(
            f"Injury Watch live coverage: {len(_v681_watch_now)} flagged players • "
            f"{_v681_q} questionable • {_v681_reserve} reserve-list • {_v681_practice} with practice status. "
            "Cached 15 minutes; manual overrides remain highest priority."
        )
        with st.expander("🩺 Fantasy Edge data health",expanded=False):
            _hc1,_hc2,_hc3,_hc4=st.columns(4)
            _hc1.metric("Injury coverage",f"{_v683_health.get('injury_coverage',0)}%")
            _hc2.metric("Matchup coverage",f"{_v683_health.get('matchup_coverage',0)}%")
            _hc3.metric("Role coverage",f"{_v683_health.get('role_coverage',0)}%")
            _hc4.metric("NFL week",f"{_v683_health.get('season')} W{_v683_health.get('week')}")
            _issues=[]
            if _v683_health.get("injury_error"): _issues.append("Injury feed: "+str(_v683_health.get("injury_error")))
            if _v683_health.get("matchup_error"): _issues.append("Matchup feed: "+str(_v683_health.get("matchup_error")))
            if _v683_health.get("role_error"): _issues.append("Role feed: "+str(_v683_health.get("role_error")))
            if _issues:
                st.warning(" | ".join(_issues))
            else:
                st.success("No current feed errors detected.")
            st.caption("Role coverage means a player has at least one current-season weekly-stat sample. It can be low before enough games have been played.")

        if st.button("🔄 Refresh injury feed now", key="v92_refresh_injuries"):
            try: sleeper_players.clear()
            except Exception: pass
            for _fn in [_v681_sleeper_injury_watch,_v680_espn_injury_watch_feed,_v680_injury_watch_feed,_v679_espn_roster_status,_v683_weekly_usage_table]:
                try: _fn.clear()
                except Exception: pass
            st.success("All injury caches cleared. Reloading live injury, practice and reserve-list statuses.")
            st.rerun()

        flagged=board[
            board["injury_effective"].fillna("ACTIVE").astype(str).str.upper().ne("ACTIVE")
            | board.get("practice_status",pd.Series("",index=board.index)).fillna("").astype(str).str.strip().ne("")
            | board.get("injury_detail",pd.Series("",index=board.index)).fillna("").astype(str).str.strip().ne("")
        ].copy()

        # Keep the default Injury Center focused ONLY on players who are actually
        # present on the certified v9 production board. The "Show all" toggle can
        # still expose the complete Sleeper injury/status feed.
        certified_keys=set()
        try:
            pb_v92,_=load_v9_production()
            if not pb_v92.empty and "key" in pb_v92.columns:
                certified_keys=set(pb_v92["key"].dropna().astype(str))
        except Exception:
            certified_keys=set()

        draft_relevant=flagged["key"].astype(str).isin(certified_keys)
        relevant_flagged=flagged[draft_relevant].copy()
        show_all_injuries=st.toggle(
            "Show all injured/status players",
            value=False,
            key="v92_show_all_injuries",
            help="Off = injured/status players on the certified production board only. Turn on to inspect every flagged player in the merged Injury Watch feed."
        )
        display_flagged=flagged if show_all_injuries else relevant_flagged

        if len(display_flagged):
            display_flagged["Penalty"]=display_flagged["injury_penalty"].map(
                lambda v:"DO NOT DRAFT" if v>=900 else f"-{v:.0f}"
            )
            display_flagged["Risk"]=display_flagged.apply(_v682_injury_risk,axis=1)
            display_flagged["Fantasy Impact"]=display_flagged.apply(_v682_injury_impact,axis=1)
            display_flagged["Roster Action"]=display_flagged.apply(_v682_injury_action,axis=1)
            display_flagged["Role"]=display_flagged.apply(_v683_role_summary,axis=1)
            display_flagged["Beneficiary"]=display_flagged.apply(lambda r:_v683_find_beneficiary(r,board,state),axis=1)
            display_flagged["Owner"]=display_flagged["player"].map(
                lambda n:"MY TEAM" if _player_owner(state,n)=="1"
                else "FREE AGENT" if _is_free_agent(state,n)
                else "ROSTERED"
            )
            _inj_scope=st.radio(
                "Injury scope",
                ["All flagged","My team","Free agents"],
                horizontal=True,
                key="v682_injury_scope"
            )
            if _inj_scope=="My team":
                display_flagged=display_flagged[display_flagged["Owner"].eq("MY TEAM")]
            elif _inj_scope=="Free agents":
                display_flagged=display_flagged[display_flagged["Owner"].eq("FREE AGENT")]

            _urgent=int(display_flagged["Risk"].astype(str).str.contains("UNAVAILABLE|HIGH",regex=True).sum()) if len(display_flagged) else 0
            c1,c2,c3=st.columns(3)
            c1.metric("Flagged",len(display_flagged))
            c2.metric("High / unavailable",_urgent)
            c3.metric("My-team flags",int((display_flagged["Owner"]=="MY TEAM").sum()) if len(display_flagged) else 0)

            display_flagged=display_flagged.sort_values(
                ["injury_penalty","player"],ascending=[False,True]
            )
            st.caption(
                f"Showing {len(display_flagged)} "
                + ("injured/status players." if show_all_injuries else "certified-board injured/status players.")
            )
            st.dataframe(
                display_flagged[["player","position","team","Owner","injury_designation","practice_display","injury_detail","Role","Risk","Fantasy Impact","Roster Action","Beneficiary","injury_updated","injury_source"]]
                .rename(columns={
                    "injury_designation":"Status",
                    "practice_display":"Practice",
                    "injury_detail":"Injury",
                    "injury_updated":"Updated",
                    "injury_source":"Source"
                })
                .head(100),
                use_container_width=True,hide_index=True
            )
        else:
            if len(flagged) and not show_all_injuries:
                st.caption("No injured/status players from the certified production board right now. Turn on “Show all” to inspect the full feed.")
            else:
                st.caption("No injury designations are currently attached to players on the board.")

        st.markdown("**Manual injury override**")
        injury_player=st.selectbox("Player",[""]+board["player"].sort_values().tolist(),key="v92_injury_player")
        injury_status=st.selectbox(
            "Override status",
            ["AUTO","ACTIVE","QUESTIONABLE","DOUBTFUL","OUT","PUP","IR","NFI","SUSPENDED","DO NOT DRAFT"],
            key="v92_injury_status"
        )
        csave,cclear=st.columns(2)
        if csave.button("💾 Save injury override",use_container_width=True) and injury_player:
            ovs=dict(state.get("injury_overrides",{}) or {})
            k=norm(injury_player)
            if injury_status=="AUTO":
                ovs.pop(k,None)
            else:
                ovs[k]=injury_status
            state["injury_overrides"]=ovs
            save_state(state)
            st.success(f"{injury_player}: {injury_status}")
            st.rerun()
        if cclear.button("Clear all manual overrides",use_container_width=True):
            state["injury_overrides"]={}
            save_state(state)
            st.success("Manual injury overrides cleared.")
            st.rerun()

    x=board[~board["player"].isin(set(state["taken"]))].copy()

    myb=board[board["player"].isin(state["my_team"])].copy()
    counts=myb.position.value_counts().to_dict()
    slots=state["roster_slots"]

    live_round=max(1,int(len(state["taken"])//max(int(teams),1))+1)
    current_overall=max(1,len(state["taken"])+1)
    _randomness=int(state.get("mock",{}).get("randomness",6))

    x,live_next=prepare_user_draft_candidates(
        x,myb,live_round,current_overall,int(live_slot),int(teams),slots,_randomness
    )
    if x.empty:
        st.warning("No eligible players remain under the current roster rules.")
        st.stop()

    cr=pd.to_numeric(x["market_pick"],errors="coerce").fillna(current_overall)
    local,ready,survive=execution_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),
        current_overall,live_next,state.get("mock",{}).get("randomness",6)
    )
    intercept_local,intercepted,intercept_fall=faller_intercept_choice(
        x.evaluation_score.to_numpy(float),cr.to_numpy(float),current_overall,local,
        teams=int(teams),rounds=exact_roster_rounds(slots)
    )
    dyn_min_fall,dyn_band,dyn_improve=dynamic_faller_threshold(current_overall,int(teams),exact_roster_rounds(slots))


    st.caption(f"Dynamic Faller Intercept this round: {dyn_min_fall:.0f}+ picks past market • top {dyn_band} model targets • {dyn_improve:.0f}-pick improvement required"
               + (" • LATE-ROUND VALUE HARVEST ACTIVE" if live_round>=11 else ""))
    # v9.43 kicker requirement: K is a real ranked candidate and the final roster slot is protected.
    _v943_kicker_needed = int(slots.get("K",1)) > int((myb.position=="K").sum() if len(myb) else 0)
    if _v943_kicker_needed and int(live_round)>=15:
        st.info("🦵 KICKER REQUIREMENT ACTIVE: 1 K is still required. The engine will preserve the final pick for K and rank available kickers from current market data.")

    # Two-track dashboard: evaluation and execution are intentionally separate.
    context_pool=apply_v933_context_quality_gate(x,myb,live_round,current_overall)
    model_targets=context_pool.sort_values("context_score",ascending=False).head(8).copy()
    draft_now=x[x.timing_ready].sort_values("execution_score",ascending=False).head(5).copy()
    if draft_now.empty:
        draft_now=x.head(5).copy()

    if len(model_targets):
        mt=model_targets.iloc[0]
        mt_action,mt_surv=market_timing_state(mt.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        st.info(f"🎯 MODEL CONTEXT: {mt.player} ({mt.position}, {mt.team}) — {mt_action}")
        mp="—" if pd.isna(mt.market_pick) else f"#{int(round(mt.market_pick))}"
        sv="—" if pd.isna(mt_surv) else f"{mt_surv:.0%}"
        st.caption(f"Model evaluation #{int(mt.evaluation_rank) if pd.notna(mt.evaluation_rank) else 999} • market {mp} • chance available next pick {sv} • current #{current_overall} → next {('#'+str(live_next)) if live_next else '—'}")

    if intercepted and intercept_local is not None and 0 <= int(intercept_local) < len(cr):
        # Context only; do not let positional intercept indexing control the final pick.
        pass
    if len(draft_now):
        dn=draft_now.iloc[0]
        dn_action,dn_surv=market_timing_state(dn.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        st.success(f"🏆 FINAL PICK: {dn.player} ({dn.position}, {dn.team}) — {dn_action}")
        st.caption(f"Authoritative roster-adjusted recommendation • evaluation #{int(dn.evaluation_rank) if pd.notna(dn.evaluation_rank) else 999} • market {('—' if pd.isna(dn.market_pick) else '#'+str(int(round(dn.market_pick))))}")

    # Persistent target queue: automatically track high-evaluation players we intentionally pass on.
    if "v761_target_queue" not in st.session_state:
        st.session_state.v761_target_queue={}
    queue=st.session_state.v761_target_queue
    available_names=set(x.player)
    for name in list(queue):
        if name not in available_names:
            queue.pop(name,None)
    for _,r in model_targets.iterrows():
        action,surv=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
        if action=="WAIT / TARGET NEXT PICK":
            queue[r.player]={"market_pick":None if pd.isna(r.market_pick) else float(r.market_pick),
                             "evaluation_rank":int(r.evaluation_rank) if pd.notna(r.evaluation_rank) else 999,"position":r.position,"team":r.team}
    # Remove queue players whose timing window has opened; they are now DRAFT NOW targets.
    for name in list(queue):
        rr=x[x.player.eq(name)]
        if len(rr):
            r=rr.iloc[0]
            action,_=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
            if action!="WAIT / TARGET NEXT PICK":
                queue.pop(name,None)
    st.session_state.v761_target_queue=queue

    if queue:
        qrows=[]
        for name,data in queue.items():
            rr=x[x.player.eq(name)]
            if not len(rr): continue
            r=rr.iloc[0]
            action,surv=market_timing_state(r.market_pick,current_overall,live_next,state.get("mock",{}).get("randomness",6))
            qrows.append({"Target":name,"Pos":r.position,"Model target #":int(r.evaluation_rank) if pd.notna(r.evaluation_rank) else 999,
                          "Market pick":"—" if pd.isna(r.market_pick) else int(round(r.market_pick)),
                          "Chance survives":"—" if pd.isna(surv) else f"{surv:.0%}","Status":action})
        if qrows:
            st.markdown("### 🎯 Target Queue")
            st.caption("Players Fantasy Edge likes but is intentionally waiting on. They leave the queue when their draft window opens or another team takes them.")
            st.dataframe(pd.DataFrame(qrows).sort_values("Model target #"),use_container_width=True,hide_index=True)

    # V6.29: live draft intelligence layer. DISPLAY ONLY — it does not alter
    # the certified recommendation/scoring engine.
    _live_log=pd.DataFrame(state.get("draft_log",[]) or [])
    _recent_n=min(10,len(_live_log))
    _recent=_live_log.tail(_recent_n).copy() if _recent_n else pd.DataFrame()
    _run_counts={}
    if len(_recent) and "position" in _recent.columns:
        _run_counts=_recent["position"].astype(str).value_counts().to_dict()
    _hot_runs=[(pos,int(n)) for pos,n in _run_counts.items() if pos in ["QB","RB","WR","TE","DL","DB"] and int(n)>=3]
    if _hot_runs:
        _hot_runs=sorted(_hot_runs,key=lambda z:z[1],reverse=True)
        st.warning("🔥 POSITION RUN: "+" • ".join([f"{n} {pos}s in the last {_recent_n} picks" for pos,n in _hot_runs[:3]])+". Check survival and tier depth before waiting.")

    # Tier-cliff monitor: compare each position's best remaining projection with
    # the 4th remaining option. This is informational only and intentionally
    # leaves the production engine untouched during a live draft.
    _cliff_rows=[]
    for _pos in ["RB","WR","QB","TE","DL","DB"]:
        _px=x[x.position.eq(_pos)].copy()
        if not len(_px): continue
        _px["_proj"]=pd.to_numeric(_px.get("projection",0),errors="coerce").fillna(0.0)
        _px=_px.sort_values(["evaluation_score","_proj"],ascending=False)
        _best=_px.iloc[0]
        _look=min(3,len(_px)-1)
        _later=_px.iloc[_look]
        _drop=max(float(_best._proj)-float(_later._proj),0.0)
        _pct=(_drop/max(abs(float(_best._proj)),1e-9))*100.0
        _surv=pd.to_numeric(pd.Series([_best.get("survival_next",np.nan)]),errors="coerce").iloc[0]
        _cliff_rows.append({"Pos":_pos,"Best":str(_best.player),"Best PPG":round(float(_best._proj),1),
                            "PPG drop by option 4":round(_drop,1),"Tier drop":f"{_pct:.0f}%",
                            "Survives next":"—" if pd.isna(_surv) else f"{float(_surv):.0%}"})
    if _cliff_rows:
        _cdf=pd.DataFrame(_cliff_rows).sort_values("PPG drop by option 4",ascending=False)
        with st.expander("📉 Tier cliffs & wait risk",expanded=True):
            st.caption("Live warning layer only. Bigger PPG drops mean the position gets materially weaker within the next few options; survival estimates whether the current best option reaches your next pick.")
            st.dataframe(_cdf,use_container_width=True,hide_index=True)

    # Explain the final recommendation with the most decision-useful components
    # already produced by the certified engine. No component is recomputed here.
    if len(draft_now):
        _er=draft_now.iloc[0]
        _parts=[]
        for _col,_label in [("roster_opportunity_adj","Roster fit"),("tier_cliff_component","Tier cliff"),
                            ("replacement_loss_component","Wait loss"),("lineup_improvement_component","Lineup gain"),
                            ("room_run_pressure_component","Room pressure"),("cross_position_cost_component","Opp. cost")]:
            _v=pd.to_numeric(pd.Series([_er.get(_col,np.nan)]),errors="coerce").iloc[0]
            if pd.notna(_v) and abs(float(_v))>=0.05: _parts.append(f"{_label} {float(_v):+.1f}")
        if _parts:
            st.caption("Why this pick: "+" • ".join(_parts))

    # Opponent roster snapshot when team labels have been entered. We avoid
    # pretending to know needs when owners are blank or inconsistently labeled.
    if len(_live_log) and {"team","position"}.issubset(_live_log.columns):
        _opp=_live_log.copy()
        _opp["team"]=_opp["team"].fillna("").astype(str).str.strip()
        _opp=_opp[~_opp["team"].isin(["","My Team"])]
        if len(_opp):
            _snap=pd.crosstab(_opp["team"],_opp["position"]).reindex(columns=["QB","RB","WR","TE","DL","DB","K"],fill_value=0)
            with st.expander("👥 Opponent roster intelligence",expanded=False):
                st.caption("Uses only the opponent-team labels you record. Blank/inconsistent team names are not guessed.")
                st.dataframe(_snap,use_container_width=True)

    # Log quality guard: flag missing opponent labels and impossible duplicate
    # overall-pick numbers before they can contaminate opponent-needs analysis.
    if len(_live_log):
        _issues=[]
        if "overall_pick" in _live_log.columns and _live_log["overall_pick"].duplicated().any(): _issues.append("duplicate overall-pick numbers")
        if {"owner","team"}.issubset(_live_log.columns):
            _blankopp=_live_log[(_live_log.owner.astype(str)=="Opponent") & (_live_log.team.fillna("").astype(str).str.strip().eq(""))]
            if len(_blankopp): _issues.append(f"{len(_blankopp)} opponent pick(s) missing team labels")
        if _issues: st.info("🧹 Draft-log quality: "+"; ".join(_issues)+". Recommendations still work, but opponent-needs estimates are less reliable.")

    # V6.46: full available-player database is intentionally separate from the
    # recommendation eligibility pool (`x`). Recommendation rules may suppress a
    # player for roster feasibility/injury/timing, but that must never make a real
    # fantasy player disappear from the database.
    with st.expander("📚 Full available player database", expanded=False):
        _db=board[~board["player"].astype(str).isin(set(map(str,state.get("taken",[]))))].copy()
        _db_pos=st.multiselect(
            "Database position",["QB","RB","WR","TE","K","DL","DB"],
            default=["QB","RB","WR","TE","K","DL","DB"],key="v646_db_pos"
        )
        _db=_db[_db["position"].astype(str).isin(_db_pos)].copy()
        _db["projection"]=pd.to_numeric(_db.get("projection"),errors="coerce")
        _db["vorp"]=pd.to_numeric(_db.get("vorp"),errors="coerce")
        _db["market_pick"]=pd.to_numeric(_db.get("market_pick"),errors="coerce")
        _db["model_rank"]=pd.to_numeric(_db.get("model_rank"),errors="coerce")
        _eligible_names=set(x["player"].astype(str)) if len(x) else set()
        _db["Recommendation pool"]=_db["player"].astype(str).map(lambda n:"Yes" if n in _eligible_names else "No — roster/injury/feasibility filter")
        _db=_db.sort_values(["position","model_rank","market_pick","projection"],ascending=[True,True,True,False],na_position="last")
        st.caption(f"{len(_db):,} undrafted database players. This view does not hide players just because the recommendation engine is filtering them.")
        st.dataframe(
            _db[["player","position","team","projection","vorp","market_pick","model_rank","Recommendation pool"]]
            .rename(columns={"player":"Player","position":"Pos","team":"Team","projection":"Projection","vorp":"VORP","market_pick":"Market pick","model_rank":"Model rank"}),
            use_container_width=True,hide_index=True
        )

    st.markdown("**Best remaining by position**")
    poscols=st.columns(3)
    for i,pos in enumerate(["RB","WR","QB","TE","DL","DB"]):
        px=x[x["position"].eq(pos)]
        if len(px):
            r=px.iloc[0]
            with poscols[i%3]:
                _rp=float(pd.to_numeric(pd.Series([r.get("projection",0)]),errors="coerce").fillna(0).iloc[0])
                _rv=float(pd.to_numeric(pd.Series([r.get("vorp",0)]),errors="coerce").fillna(0).iloc[0])
                st.caption(f"**{pos}: {r.get('player','Unknown')}** — {_rp:.1f} PPG, VORP {_rv:+.1f}")

    pos=st.multiselect("Position",["QB","RB","WR","TE","DL","DB"],default=["QB","RB","WR","TE","DL","DB"],key="draftpos")

    # V6.49: AUTHORITATIVE VISIBLE BOARD.
    # Never construct the user-visible draft database from the mutable runtime
    # recommendation board. Rebuild it directly from the packaged production
    # database every render, then subtract only names actually recorded as taken.
    # This guarantees packaged players (for example J.K. Dobbins) cannot vanish
    # because an external refresh/recommendation transform returned a smaller pool.
    _display_master=_fast_local_draft_board()
    if _display_master is None or _display_master.empty:
        _display_master=board.copy()
    else:
        # Apply published projections to the complete packaged universe when the
        # source is available. Failure safely retains packaged projection/VORP.
        _display_master,_,_=_v645_apply_published_projections(
            _display_master,ppr,teams,state["roster_slots"]
        )

    # Overlay only runtime metadata that is useful for display; never use runtime
    # membership to determine whether a player exists in the visible database.
    if len(board):
        _runtime_overlay=board.copy()
        _runtime_overlay["_key649"]=_runtime_overlay["player"].astype(str).map(norm)
        _runtime_overlay=_runtime_overlay.drop_duplicates("_key649",keep="first").set_index("_key649")
        _display_master["_key649"]=_display_master["player"].astype(str).map(norm)
        for _c in ["team","injury","injury_source","profile","confidence"]:
            if _c in _runtime_overlay.columns:
                _mapped=_display_master["_key649"].map(_runtime_overlay[_c])
                if _c in _display_master.columns:
                    _display_master[_c]=_mapped.where(_mapped.notna(),_display_master[_c])
                else:
                    _display_master[_c]=_mapped
        _display_master=_display_master.drop(columns=["_key649"],errors="ignore")

    _taken_display=set(map(str,state.get("taken",[])))
    _display_pool=_display_master[~_display_master["player"].astype(str).isin(_taken_display)].copy()
    _rec_names=set(x["player"].astype(str)) if len(x) else set()
    _display_pool["recommendation_pool"]=_display_pool["player"].astype(str).map(
        lambda n: "Yes" if n in _rec_names else "No — model filtered"
    )

    # Overlay dynamic recommendation fields without replacing the authoritative
    # production projection/VORP/market identity fields for filtered players.
    if len(x):
        _xr=x.drop_duplicates(subset=["player"],keep="first").set_index("player")
        _dynamic_cols=[
            "evaluation_rank","survival_next","roster_opportunity_adj",
            "idp_external_rank","idp_impact_score","profile","confidence",
            "injury","injury_source","final_pick_value","execution_score"
        ]
        for _c in _dynamic_cols:
            if _c in _xr.columns:
                _mapped=_display_pool["player"].map(_xr[_c])
                if _c in _display_pool.columns:
                    _display_pool[_c]=_mapped.where(_mapped.notna(),_display_pool[_c])
                else:
                    _display_pool[_c]=_mapped

    # V6.48: visibility and ordering are independent from recommendation eligibility.
    # Every undrafted production player stays in the table.  Use the dynamic
    # evaluation rank when the decision engine produced one; otherwise fall back
    # to the player's packaged production model rank.  Never push model-filtered
    # players below an arbitrary recommendation-only block.
    _display_pool["_eval_sort"]=pd.to_numeric(_display_pool.get("evaluation_rank",np.nan),errors="coerce")
    _display_pool["_model_sort"]=pd.to_numeric(_display_pool.get("model_rank",np.nan),errors="coerce")
    _display_pool["_target_sort"]=_display_pool["_eval_sort"].where(_display_pool["_eval_sort"].notna(),_display_pool["_model_sort"])
    _display_pool["_market_sort"]=pd.to_numeric(_display_pool.get("market_pick",np.nan),errors="coerce")
    _display_pool=_display_pool.sort_values(
        ["_target_sort","_market_sort","projection"],
        ascending=[True,True,False],na_position="last"
    )
    show=_display_pool[_display_pool.position.isin(pos)].copy()

    # V6.49 direct player lookup + auditable pool counts. This makes it obvious
    # whether a packaged player exists before any sorting/display formatting.
    _find_player=st.text_input("Find player",value="",placeholder="Type a name, e.g. J.K. Dobbins",key="v649_find_player")
    if str(_find_player).strip():
        _needle=norm(str(_find_player).strip())
        show=show[show["player"].astype(str).map(norm).str.contains(_needle,regex=False)].copy()
    _remaining_counts=_display_pool["position"].astype(str).value_counts().to_dict()
    st.caption(
        "Authoritative packaged pool: " + str(len(_display_master)) +
        " players • Undrafted: " + str(len(_display_pool)) +
        " • RB " + str(int(_remaining_counts.get("RB",0))) +
        " • WR " + str(int(_remaining_counts.get("WR",0)))
    )
    _v652_rows,_v652_has_dobbins=_v652_embedded_board_diagnostic()
    st.caption(f"Build: {V651_BUILD_ID} • Direct embedded rows: {_v652_rows} • Dobbins embedded: {'YES' if _v652_has_dobbins else 'NO'} • Rendered master rows: {len(_display_master)}")

    show["Profile"]=show["profile"] if "profile" in show.columns else "Stable / neutral"
    show["Confidence"]=(show["confidence"] if "confidence" in show.columns else pd.Series(0.50,index=show.index)).map(lambda v:f"{float(v):.0%}")
    show["Market pick"]=(show["market_pick"] if "market_pick" in show.columns else pd.Series(np.nan,index=show.index)).map(lambda v:"—" if pd.isna(v) else int(round(v)))
    show["Action"]=[market_timing_state(mp,current_overall,live_next,state.get("mock",{}).get("randomness",6))[0] for mp in (show["market_pick"] if "market_pick" in show.columns else pd.Series(np.nan,index=show.index))]
    show["Survives next"]=(show["survival_next"] if "survival_next" in show.columns else pd.Series(np.nan,index=show.index)).map(lambda v:"—" if pd.isna(v) else f"{float(v):.0%}")
    # V6.36: never fabricate a shared model rank for unscored roster-only players.
    # A missing evaluation_rank means Fantasy Edge has identity only, not enough
    # projection/market evidence to produce a trustworthy model target number.
    _eval_rank_display=pd.to_numeric(show.get("evaluation_rank",np.nan),errors="coerce")
    _prod_rank_display=pd.to_numeric(show.get("model_rank",np.nan),errors="coerce")
    _target_rank_display=_eval_rank_display.where(_eval_rank_display.notna(),_prod_rank_display)
    show["Model target #"]=_target_rank_display.map(
        lambda v: "—" if pd.isna(v) else str(int(round(float(v))))
    )
    show["Faller picks"]=np.maximum(current_overall-pd.to_numeric(show["market_pick"] if "market_pick" in show.columns else pd.Series(np.nan,index=show.index),errors="coerce"),0)
    show["Faller picks"]=show["Faller picks"].map(lambda v:"—" if pd.isna(v) or v<1 else f"+{v:.0f}")
    def _v934_public_reason(rr):
        p=str(rr.get("position",""))
        counts_now=myb.position.value_counts().to_dict() if myb is not None and len(myb) else {}
        if p in ["DL","DB"]:
            impact,eligible,evidence=_v934_idp_impact_score(rr)
            if counts_now.get(p,0)<1:
                return f"{p} starter need • impact {impact:.1f}" if eligible else f"{p} starter need • low evidence"
            return f"Optional {p} depth • impact {impact:.1f}" if eligible else f"Optional {p} depth • low evidence"
        if p=="QB" and counts_now.get("QB",0)>=1: return "QB2 bench value"
        if p=="TE" and counts_now.get("TE",0)>=1: return "TE2/FLEX value"
        if p=="WR": return "WR/FLEX depth"
        if p=="RB": return "RB/FLEX depth"
        return "Roster fit / value"
    show["Recommendation reason"]=show.apply(_v934_public_reason,axis=1)
    # V6.55 display: missing published offense is shown explicitly, never as a
    # repeated numeric bucket. Keep numeric sort columns intact and create text
    # columns only for the user-facing/export table.
    _proj_num=pd.to_numeric(show.get("projection",np.nan),errors="coerce")
    _vorp_num=pd.to_numeric(show.get("vorp",np.nan),errors="coerce")
    show["Projection"]=_proj_num.map(lambda v:"No projection" if pd.isna(v) else f"{float(v):.2f}")
    show["VORP display"]=_vorp_num.map(lambda v:"—" if pd.isna(v) else f"{float(v):+.2f}")
    show["Projection source"]=show.get("projection_source",pd.Series("",index=show.index)).fillna("")
    _draft_display_defaults={
        "team":"NFL","projection":np.nan,"vorp":np.nan,
        "idp_external_rank":np.nan,"idp_impact_score":np.nan,
        "roster_opportunity_adj":0.0,"injury":"","injury_source":"Local",
        "profile":"Stable / neutral","confidence":0.50,"survival_next":np.nan,
        "evaluation_rank":np.nan,"market_pick":np.nan,
    }
    for _c,_default in _draft_display_defaults.items():
        if _c not in show.columns:
            show[_c]=_default
    st.caption(f"Showing {len(show):,} undrafted players from the authoritative packaged production database. ‘Recommendation pool’ shows whether the decision engine currently considers that player eligible, but filtered players remain visible.")
    st.dataframe(
        show[["player","position","team","Model target #","Action","Market pick","Faller picks",
              "Survives next","Projection","VORP display","Projection source","idp_external_rank","idp_impact_score","roster_opportunity_adj","recommendation_pool","Recommendation reason",
              "Profile","Confidence","injury","injury_source"]]
        .rename(columns={
            "injury":"Injury","injury_source":"Injury source",
            "idp_external_rank":"IDP rank","idp_impact_score":"IDP impact","usable_vorp":"Usable VORP","marginal_roster_value":"Marginal roster value","bench_startability":"Bench startability","tier_cliff_component":"Tier cliff","replacement_loss_component":"Next-turn loss","lineup_improvement_component":"Lineup gain","next_turn_survival_component":"Survival %","cross_position_cost_component":"Opportunity cost","future_roster_component":"Future roster","rollout_value":"2-pick rollout","final_pick_value":"Final pick value","challenger_gap":"Challenger gap","room_run_pressure_component":"Room pressure","candidate_stability":"Stability","base_player_value":"Base value","marginal_slot_value":"Marginal slot","wait_cost":"Wait cost","survival_probability":"Next-pick survival","strategic_pick_value":"Strategic value","rollout_value":"Rollout","expected_regret":"Expected regret","recommendation_confidence":"Confidence %","value_over_next_roster_slot":"Value over next slot","idp_available_rank":"Available IDP rank","idp_available_score":"Available IDP score","roster_opportunity_adj":"Roster opp."
        }),
        use_container_width=True,hide_index=True
    )

    st.markdown("### Record the latest pick")
    # V6.20: recording a real Yahoo pick must use the FULL available master pool,
    # not the position-filtered recommendation table. The old selector inherited
    # `show`, so unchecked position filters could make elite players disappear.
    # V6.35: simple Live Draft picker + roster-directory names only.
    # Roster-only players never enter `board`, so they cannot inherit fake/common
    # projections, market picks, VORP, ranks, or recommendation scores.
    # V6.54: canonicalize player identity before building the picker. Multiple
    # feeds can spell the same NFL player differently (for example Luther Burden
    # vs Luther Burden III, Chris Rodriguez vs Chris Rodriguez Jr., or Deebo
    # Samuel vs Deebo Samuel Sr.). `norm()` intentionally removes generational
    # suffixes, punctuation and spacing, so use that identity key here instead
    # of raw display strings. Production-board names are authoritative; the
    # active-roster directory only fills players not already represented.
    _taken_names=set(map(str,state.get("taken",[])))
    _taken_keys={norm(_n) for _n in _taken_names if norm(_n)}
    _record_by_key={}

    _board_picker=board.copy()
    if len(_board_picker):
        # When the production board itself has two aliases, keep the row with
        # the strongest model/market evidence and expose only that display name.
        _board_picker["_v654_key"]=_board_picker["player"].astype(str).map(norm)
        _board_picker["_v654_model"]=pd.to_numeric(_board_picker.get("model_rank",np.nan),errors="coerce").fillna(9999)
        _board_picker["_v654_market"]=pd.to_numeric(_board_picker.get("market_pick",np.nan),errors="coerce").fillna(9999)
        _board_picker=_board_picker.sort_values(["_v654_model","_v654_market","player"],kind="stable")
        for _name,_key in zip(_board_picker["player"].astype(str),_board_picker["_v654_key"].astype(str)):
            if _key and _key not in _taken_keys and _key not in _record_by_key:
                _record_by_key[_key]=_name

    if isinstance(_active_roster_export,pd.DataFrame) and len(_active_roster_export):
        for _name in _active_roster_export["player"].astype(str).tolist():
            _key=norm(_name)
            if _key and _key not in _taken_keys and _key not in _record_by_key:
                _record_by_key[_key]=_name

    # Preserve the currently selected roster-directory player across the submit
    # rerun, but do not reintroduce a duplicate alias.
    _session_pick=str(st.session_state.get("v640_record_pick","") or "").strip()
    if _session_pick:
        _session_key=norm(_session_pick)
        if _session_key and _session_key not in _taken_keys:
            _record_by_key.setdefault(_session_key,_session_pick)

    _record_options=sorted(_record_by_key.values(),key=str.lower)
    # V6.40: submit player + owner + opponent team atomically. Putting these
    # controls inside a form prevents Streamlit widget reruns from losing a
    # roster-directory-only player before the Record action executes.
    with st.form("v640_record_pick_form", clear_on_submit=True):
        pick=st.selectbox(
            "Player selected",
            [""]+_record_options,
            key="v640_record_pick"
        )
        pick_owner=st.radio("Who drafted him?",["Opponent","Mine"],horizontal=True,key="v640_pick_owner")
        opponent_team=st.text_input("Opponent team (optional)",key="v640_opponent_team")
        _record_clicked=st.form_submit_button("➕ Record draft pick",type="primary")

    if _record_clicked:
        _commit_pick=str(pick or "").strip()
        if not _commit_pick:
            st.warning("Choose a player before recording the pick.")
        elif norm(_commit_pick) in {norm(_n) for _n in state.get("taken",[]) if norm(_n)}:
            st.warning(f"{_commit_pick} is already marked as drafted (including name/suffix aliases).")
        else:
            if pick_owner=="Mine":
                state["my_team"]=list(dict.fromkeys(list(state.get("my_team",[]))+[_commit_pick]))
            state["taken"]=list(dict.fromkeys(list(state.get("taken",[]))+[_commit_pick]))

            # V6.74 hard ownership guard: a recorded draft pick can never remain FA.
            state=_ensure_ownership_state(state,all_names)
            _pick_key=_owner_key(_commit_pick)
            if pick_owner=="Mine":
                _pick_owner_id="1"
            else:
                _pick_owner_id="ROSTERED_UNKNOWN"
                _opp=str(opponent_team or "").strip()
                _opp_lower=_opp.lower()
                # Resolve either a numbered team label or one of the saved team names.
                _m=re.search(r"(?:team\s*)?(\d+)$",_opp_lower)
                if _m and 1 <= int(_m.group(1)) <= int(teams):
                    _pick_owner_id=str(int(_m.group(1)))
                else:
                    for _tid,_tname in (state.get("team_names") or {}).items():
                        if _opp and str(_tname).strip().lower()==_opp_lower:
                            _pick_owner_id=str(_tid)
                            break
            state["ownership"][_pick_key]={"player":_commit_pick,"owner":_pick_owner_id}

            log=list(state.get("draft_log",[]))

            # Resolve position for display only. A missing projection-board row
            # can never prevent the pick from being committed.
            prow=board[board["player"].astype(str).eq(_commit_pick)]
            if len(prow):
                ppos=str(prow.iloc[0].position)
            elif isinstance(_active_roster_export,pd.DataFrame) and len(_active_roster_export):
                _rr=_active_roster_export[_active_roster_export["player"].astype(str).eq(_commit_pick)]
                ppos=str(_rr.iloc[0].position) if len(_rr) else ""
            else:
                ppos=""

            _existing_overalls=[]
            for _entry in log:
                try:
                    _existing_overalls.append(int(_entry.get("overall_pick",0) or 0))
                except Exception:
                    pass
            _next_overall=(max(_existing_overalls) if _existing_overalls else 0)+1
            log.append({"overall_pick":_next_overall,"round":int(live_round),"owner":str(pick_owner),
                        "team":("My Team" if pick_owner=="Mine" else str(opponent_team or "")),
                        "player":_commit_pick,"position":ppos})
            state["draft_log"]=log
            state=_ensure_ownership_state(state,all_names)
            state=_sync_legacy_from_ownership(state)
            save_state(state)
            # V6.41: the form clears its own widget values on successful submit.
            # Do not mutate widget-backed session_state keys after instantiation;
            # Streamlit raises StreamlitAPIException when doing so.
            st.rerun()

    if state.get("draft_log"):
        with st.expander("📋 Live draft log",expanded=False):
            logdf=pd.DataFrame(state["draft_log"])
            st.dataframe(logdf.tail(30),use_container_width=True,hide_index=True)
            st.download_button("⬇️ Download draft log",logdf.to_csv(index=False).encode("utf-8"),
                               "fantasy_edge_live_draft_log.csv","text/csv")

    # v9.1 draft correction controls
    st.markdown("### Draft controls")
    undo_col, reset_col = st.columns(2)

    if undo_col.button("↩️ Undo Last Pick", use_container_width=True):
        log=list(state.get("draft_log",[]))
        if not log:
            st.warning("There are no recorded picks to undo.")
        else:
            last=log.pop()
            player=last.get("player")
            owner=last.get("owner")

            # Remove one occurrence from taken.
            taken=list(state.get("taken",[]))
            if player in taken:
                taken.remove(player)
            state["taken"]=taken

            # If it was my pick, also remove one occurrence from my roster.
            if owner=="Mine":
                mine=list(state.get("my_team",[]))
                if player in mine:
                    mine.remove(player)
                state["my_team"]=mine

            state["draft_log"]=log
            save_state(state)
            st.success(f"Undid last pick: {player or 'unknown player'}")
            st.rerun()

    if "confirm_reset_draft_v91" not in st.session_state:
        st.session_state.confirm_reset_draft_v91=False

    if reset_col.button("🗑️ Reset Entire Draft", use_container_width=True):
        st.session_state.confirm_reset_draft_v91=True

    if st.session_state.confirm_reset_draft_v91:
        st.warning("This will clear every recorded Mine/Opponent pick and your current draft roster.")
        c_yes,c_no=st.columns(2)
        if c_yes.button("✅ Yes, reset draft", type="primary", use_container_width=True):
            state["taken"]=[]
            state["my_team"]=[]
            state["draft_log"]=[]
            # Clear older live-draft queues if present so a new draft is truly clean.
            st.session_state.pop("v761_target_queue",None)
            st.session_state.confirm_reset_draft_v91=False
            save_state(state)
            st.success("Draft reset. All players are available again.")
            st.rerun()
        if c_no.button("Cancel reset", use_container_width=True):
            st.session_state.confirm_reset_draft_v91=False
            st.rerun()

with tabs[2]:
    st.subheader("🧪 Mock Draft Lab")
    st.caption("12-team SNAKE draft: practice the exact turn order, test Fantasy Edge against consensus, and measure whether the model actually creates value.")
    st.success("🔒 Live Draft and Mock Draft Lab use the same player pool and recommendation logic.")

    m=state["mock"]
    c1,c2,c3=st.columns(3)
    slot=c1.number_input("Your draft slot",1,12,min(int(m.get("draft_slot",1)),12))
    rounds=17
    c2.number_input(
        "Rounds",min_value=17,max_value=17,value=17,disabled=True,
        key="v9441_exact_rounds",
        help="Locked to your exact 17-player roster."
    )
    randomness=c3.slider("Draft-room randomness",4,30,int(m.get("randomness",12)),
                         help="Higher values make computer teams deviate more from consensus.")
    state["mock"]={"draft_slot":int(slot),"rounds":int(rounds),"randomness":int(randomness)}

    mode=st.radio("Test mode",["Interactive mock","Automated 100-draft test"],horizontal=True)
    st.caption("Snake order check: R1 runs 1→12, R2 runs 12→1, then alternates every round.")
    st.caption("Exact league construction: 1 QB • 2 RB • 2 WR • 1 TE • 2 FLEX • 1 K • 1 DL • 1 DB • 6 Bench • 17 rounds.")
    if st.button("Set validation preset: Pick 7 • 17 rounds • randomness 6",key="v731_validation_preset"):
        state["mock"]={"draft_slot":7,"rounds":17,"randomness":6}
        save_state(state)
        st.success("Validation preset saved. Refresh once if the visible controls have not updated.")

    if mode=="Interactive mock":
        if "mock_drafted" not in st.session_state:
            st.session_state.mock_drafted=[]
            st.session_state.mock_user=[]
            st.session_state.mock_overall=1
            st.session_state.mock_opp_rosters={i:[] for i in range(1,13)}

        a,b=st.columns(2)
        if a.button("Start / reset mock"):
            st.session_state.mock_drafted=[]
            st.session_state.mock_user=[]
            st.session_state.mock_overall=1
            st.session_state.mock_opp_rosters={i:[] for i in range(1,13)}
            st.rerun()
        if b.button("Auto-draft opponents until my next pick"):
            drafted=st.session_state.mock_drafted
            overall=st.session_state.mock_overall
            rng=np.random.default_rng(overall+int(slot))
            while overall<=int(teams)*int(rounds):
                rnd=(overall-1)//int(teams)+1
                pir=(overall-1)%int(teams)+1
                owner=pir if rnd%2 else int(teams)-pir+1
                if owner==int(slot): break
                avail=board[~board["player"].isin(drafted)].copy()
                if avail.empty: break
                fallback=avail.model_rank
                base=avail.consensus_rank.fillna(fallback)
                noise=rng.normal(0,int(randomness),len(avail))
                avail["opp"]=base+noise

                # Opponent roster realism: each computer team also needs QB/RB/WR/TE/K/DL/DB.
                if "mock_opp_rosters" not in st.session_state:
                    st.session_state.mock_opp_rosters={i:[] for i in range(1,13)}
                opp_names=st.session_state.mock_opp_rosters.get(int(owner),[])
                opp_roster=board[board["player"].isin(opp_names)]
                oc=opp_roster.position.value_counts().to_dict() if len(opp_roster) else {}

                # Keep IDP out of premium rounds, then create realistic late need.
                if rnd<=7:
                    avail.loc[avail.position.isin(["DL","DB"]),"opp"]+=25.0
                if rnd>=9 and oc.get("DL",0)<1:
                    avail.loc[avail.position.eq("DL"),"opp"]-=7.0
                if rnd>=10 and oc.get("DB",0)<1:
                    avail.loc[avail.position.eq("DB"),"opp"]-=7.0
                if rnd>=14 and oc.get("K",0)<1:
                    avail.loc[avail.position.eq("K"),"opp"]-=8.0

                # Avoid duplicate onesies/depth excess.
                if oc.get("QB",0)>=1:
                    avail.loc[avail.position.eq("QB"),"opp"]+=12.0
                if oc.get("TE",0)>=1:
                    avail.loc[avail.position.eq("TE"),"opp"]+=8.0
                if oc.get("K",0)>=1:
                    avail.loc[avail.position.eq("K"),"opp"]+=100.0
                if oc.get("DL",0)>=1:
                    avail.loc[avail.position.eq("DL"),"opp"]+=5.0
                if oc.get("DB",0)>=1:
                    avail.loc[avail.position.eq("DB"),"opp"]+=5.0

                choice=avail.sort_values("opp").iloc[0]
                drafted.append(choice.player)
                st.session_state.mock_opp_rosters.setdefault(int(owner),[]).append(str(choice.player))
                drafted=list(dict.fromkeys(drafted))
                overall+=1
            st.session_state.mock_drafted=drafted
            st.session_state.mock_overall=overall
            st.rerun()

        overall=st.session_state.mock_overall
        if overall<=int(teams)*int(rounds):
            rnd=(overall-1)//int(teams)+1
            pir=(overall-1)%int(teams)+1
            owner=pir if rnd%2 else int(teams)-pir+1
            st.info(f"Overall pick {overall} • Round {rnd} • {'YOU ARE ON THE CLOCK' if owner==int(slot) else f'Team {owner} is picking'}")

            if owner==int(slot):
                avail=board[~board["player"].isin(st.session_state.mock_drafted)].copy()
                roster=pd.DataFrame(st.session_state.mock_user) if st.session_state.mock_user else board.iloc[0:0].copy()

                avail,nxt=prepare_user_draft_candidates(
                    avail,roster,rnd,overall,int(slot),int(teams),state["roster_slots"],randomness
                )
                if avail.empty:
                    st.warning("No eligible available players remain for this pick.")
                    st.stop()

                cr=pd.to_numeric(avail["market_pick"],errors="coerce").fillna(overall)
                local,ready,survive=execution_choice(
                    avail.evaluation_score.to_numpy(float),cr.to_numpy(float),
                    overall,nxt,randomness
                )
                intercept_local,intercepted,intercept_fall=faller_intercept_choice(
                    avail.evaluation_score.to_numpy(float),cr.to_numpy(float),overall,local,
                    teams=int(teams),rounds=int(rounds)
                )
                # v9.23.1 availability integrity: preserve player identity BEFORE sorting.
                # intercept_local is positional to the pre-sort available pool and must never
                # be reused as an iloc after the dataframe is reordered.
                intercept_player=None
                if intercepted and intercept_local is not None and 0 <= int(intercept_local) < len(avail):
                    intercept_player=str(avail.iloc[int(intercept_local)].player)
                avail["survival_next"]=survive
                avail["timing_ready"]=ready
                # Execution score is only for ordering the UI; player evaluation remains visible separately.
                # v9.39: execution_score is shared with Draft Mode; no mock-only reranking.
                avail["live"]=avail["execution_score"]
                avail=avail.sort_values("execution_score",ascending=False)
                nxt=next_user_pick(overall,int(slot),int(teams),int(rounds))
                avail["evaluation_rank"]=avail.evaluation_score.rank(method="min",ascending=False)
                context_pool=apply_v933_context_quality_gate(avail,roster,rnd,overall)
                model_top=context_pool.sort_values("context_score",ascending=False).head(8).copy()
                now_top=avail[avail.timing_ready].sort_values("execution_score",ascending=False).head(8).copy()
                if now_top.empty: now_top=avail.head(8).copy()
                mt=model_top.iloc[0]
                mt_action,mt_surv=market_timing_state(mt.market_pick,overall,nxt,randomness)
                st.info(f"🎯 MODEL CONTEXT: {mt.player} — {mt_action}")

                available_names=set(avail.player.astype(str))
                intercept_row=None
                if intercepted and intercept_player and intercept_player in available_names:
                    rr=avail[avail.player.astype(str).eq(intercept_player)]
                    if len(rr):
                        intercept_row=rr.iloc[0]

                if intercept_row is not None:
                    st.info(f"💎 FALLER CONTEXT: {intercept_row.player} — {intercept_fall:.0f} picks past market")
                else:
                    intercepted=False
                # v9.31: exactly one authoritative recommendation. Context cards never
                # replace the roster-adjusted, timing-ready FINAL PICK.
                dn=now_top.iloc[0]
                dn_action,dn_surv=market_timing_state(dn.market_pick,overall,nxt,randomness)
                st.success(f"🏆 FINAL PICK: {dn.player} — {dn_action}")
                if nxt:
                    st.caption(f"Current pick #{overall} • next pick #{nxt}. FINAL PICK is authoritative; model/faller cards are context only.")
                top=now_top.copy()
                actions=[market_timing_state(mp,overall,nxt,randomness) for mp in top.market_pick]
                top["Action"]=[a[0] for a in actions]
                top["Survives to next pick"]=["—" if pd.isna(a[1]) else f"{a[1]:.0%}" for a in actions]
                top["Market pick"]=top.market_pick.map(lambda v:"—" if pd.isna(v) else int(round(v)))
                # V6.30 restart-safe display guard: some optional diagnostic columns
                # are only created by particular optimizer paths. Streamlit executes
                # every tab on restart, so a table must never assume those fields exist.
                _mock_display_cols=[
                    "player","position","team","evaluation_rank","Action","Market pick",
                    "Survives to next pick","projection","vorp","usable_vorp","marginal_roster_value",
                    "bench_startability","value_over_next_roster_slot","tier_cliff_component",
                    "replacement_loss_component","lineup_improvement_component","next_turn_survival_component",
                    "cross_position_cost_component","future_roster_component","rollout_value","final_pick_value",
                    "challenger_gap","room_run_pressure_component","candidate_stability","base_player_value",
                    "marginal_slot_value","wait_cost","survival_probability","strategic_pick_value",
                    "expected_regret","recommendation_confidence","idp_available_rank","idp_available_score",
                    "idp_scarcity_cliff","roster_opportunity_adj","roster_opportunity_note","profile"
                ]
                _mock_text_cols={"player","position","team","Action","Market pick","Survives to next pick","roster_opportunity_note","profile"}
                for _c in _mock_display_cols:
                    if _c not in top.columns:
                        top[_c]="—" if _c in _mock_text_cols else np.nan
                st.dataframe(
                    top[_mock_display_cols]
                    .rename(columns={
                        "idp_external_rank":"IDP rank","idp_impact_score":"IDP impact","usable_vorp":"Usable VORP","marginal_roster_value":"Marginal roster value","value_over_next_roster_slot":"Value over next slot","idp_available_rank":"Available IDP rank","idp_available_score":"Available IDP score","roster_opportunity_adj":"Roster opp.",
                        "roster_opportunity_note":"Roster reason"
                    }),
                    use_container_width=True,hide_index=True
                )
                # v9.23.1: one authoritative pool controls table, intercept and selector.
                available_names=set(avail.player.astype(str))
                pick_options=[str(p) for p in top.player.tolist() if str(p) in available_names]
                final_name=str(dn.player)
                if final_name in available_names:
                    pick_options=[final_name]+[p for p in pick_options if p!=final_name]
                # Remove duplicates while preserving recommendation order.
                pick_options=list(dict.fromkeys(pick_options))

                if not pick_options:
                    st.warning("No eligible available players remain for this pick.")
                else:
                    choice=st.selectbox("Your mock pick",pick_options)
                    if st.button("Draft this player"):
                        # Final integrity gate immediately before committing the pick.
                        current_available=board[
                            (~board["player"].isin(st.session_state.mock_drafted))
                            & (board.injury_severity<3)
                        ].copy()
                        if choice not in set(current_available.player.astype(str)):
                            st.error(f"{choice} is no longer available. Refreshing the mock board.")
                            st.rerun()
                        # Re-run the FULL available pool so comparative rules remain authoritative
                        # at commit time (same-position dominance, IDP rank, scarcity, portfolio value).
                        _commit_pool,_=prepare_user_draft_candidates(
                            current_available,roster,rnd,overall,int(slot),int(teams),state["roster_slots"],randomness
                        )
                        _commit=_commit_pool[_commit_pool.player.astype(str).eq(str(choice))].copy()
                        if _commit.empty:
                            st.error(f"{choice} is no longer eligible under the live draft rules.")
                            st.rerun()
                        row=_commit.iloc[0].to_dict()
                        row["mock_pick"]=overall; row["mock_round"]=rnd
                        st.session_state.mock_user.append(row)
                        st.session_state.mock_drafted=list(dict.fromkeys(st.session_state.mock_drafted+[choice]))
                        st.session_state.mock_overall=overall+1
                        st.rerun()
            else:
                st.caption("Tap “Auto-draft opponents until my next pick” to advance quickly.")
        else:
            st.success("Mock draft complete.")

        roster=pd.DataFrame(st.session_state.mock_user) if st.session_state.mock_user else pd.DataFrame()
        if len(roster):
            g=grade_mock(roster,int(teams),state["roster_slots"])
            st.markdown("### Live mock grade")
            x1,x2,x3=st.columns(3)
            x1.metric("Grade",g["grade"],f"{g['score']:.0f}/100")
            x2.metric("Starter VORP",f"{g['starter']:+.1f}")
            x3.metric("Avg value vs market",f"{g['value']:+.1f} spots")
            st.markdown("#### Grade breakdown")
            a,b,c,d=st.columns(4)
            a.metric("Draft Value",f"{g['draft_value']:.0f}/100")
            b.metric("Roster Construction",f"{g['construction']:.0f}/100")
            c.metric("Positional Advantage",f"{g['positional_advantage']:.0f}/100")
            d.metric("Model Edge",f"{g['model_edge_score']:.0f}/100")
            st.caption(
                f"Model Edge quality: {g.get('clean_pick_rate',0):.0%} clean picks • "
                f"{g.get('market_win_rate',0):.0%} drafted at/after market • "
                f"{g.get('big_reach_rate',0):.0%} big reaches • "
                f"{g.get('portfolio_penalty',0):.1f} portfolio penalty."
            )
            if g.get("opportunity_penalty",0)>0:
                st.caption(f"Opportunity-cost adjustment: -{g['opportunity_penalty']:.1f}")
            if g.get("penalty",0)>0:
                st.warning(f"Roster-construction penalty: -{g['penalty']:.0f} grade points")
            counts=roster.position.value_counts().to_dict()
            st.caption("Roster build: " + " • ".join(f"{p} {counts.get(p,0)}" for p in ["QB","RB","WR","TE","DL","DB"]))
            _show=roster.copy()
            for _c,_raw in [("display_projection","projection"),("display_vorp","vorp"),("display_model_rank","model_rank")]:
                if _c not in _show.columns: _show[_c]=_show.get(_raw,np.nan)
            st.dataframe(
                _show[["mock_round","mock_pick","player","position","display_projection","display_vorp","display_model_rank","consensus_rank","profile"]]
                .rename(columns={"display_projection":"Model/IDP score","display_vorp":"VORP / roster impact","display_model_rank":"Model / IDP rank"}),
                use_container_width=True,hide_index=True
            )

    else:
        st.markdown("### 🧪 Automated 100-Draft Test")
        st.caption(
            "This uses the same Fantasy Edge candidate preparation, roster balance, saturation, "
            "projection/VORP, kicker, IDP, reach, timing, marginal roster value, bench optimizer, "
            "and FINAL PICK execution-score logic used by the interactive mock."
        )

        st.info(
            "⚡ Fast simulation mode: your 17 picks use the full Fantasy Edge engine. "
            "Opponent picks use a lightweight market/roster model so 100 drafts finish much faster."
        )
        target_sims=100
        _benchmark_build="FE-V6.11-MERIT-IDP-SNAKE-WAIT-20260827"
        if st.session_state.get("fe_benchmark_build")!=_benchmark_build:
            st.session_state.fe1000_results=[]
            st.session_state.fe1000_next_seed=910000
            st.session_state.fe_benchmark_failures=[]
            st.session_state.fe_benchmark_build=_benchmark_build

        batch_size=st.selectbox(
            "Drafts per run batch",
            options=[1,2,4,8],
            index=0,
            help="Drafts run in parallel. 4 is the recommended Streamlit Cloud batch size after profiling; larger batches may contend for CPU."
        )

        if "fe1000_results" not in st.session_state:
            st.session_state.fe1000_results=[]
        if "fe1000_next_seed" not in st.session_state:
            st.session_state.fe1000_next_seed=910000
        if "fe_benchmark_failures" not in st.session_state:
            st.session_state.fe_benchmark_failures=[]

        done=len(st.session_state.fe1000_results)
        st.progress(min(done/target_sims,1.0))
        st.caption(f"Completed {done:,} / {target_sims:,} automated drafts.")
        st.caption("Failed seeds are retried automatically on the next Run; successful drafts are kept.")
        if st.session_state.get("fe_benchmark_failures"):
            _fails=st.session_state.fe_benchmark_failures
            st.error(f"Benchmark engine failures: {len(_fails)}. Press Run again to retry failed seeds; completed drafts are preserved.")
            with st.expander("Show benchmark failures", expanded=True):
                for _f in _fails[-8:]:
                    st.code(f"seed {_f.get('seed')}: {_f.get('error')}",language=None)
        if st.session_state.get("fe_last_batch_seconds"):
            _secs=float(st.session_state["fe_last_batch_seconds"])
            _rate=float(st.session_state.get("fe_last_batch_rate",0.0))
            _remaining=max(target_sims-done,0)
            _eta=(_remaining/_rate) if _rate>0 else 0.0
            st.caption(f"Last batch: {_secs:.1f}s • {_rate:.2f} drafts/sec • estimated remaining runtime: {_eta/60:.1f} min")

        a,b=st.columns(2)
        run=a.button(
            "▶️ Run / continue 100-draft test",
            type="primary",
            disabled=done>=target_sims,
            key="fe1000_run"
        )
        reset=b.button("Reset simulation test",key="fe1000_reset")

        if reset:
            st.session_state.fe1000_results=[]
            st.session_state.fe1000_next_seed=910000
            st.session_state.fe_benchmark_failures=[]
            st.session_state.pop("fe_last_batch_seconds",None)
            st.session_state.pop("fe_last_batch_rate",None)
            st.rerun()

        if run:
            remaining=target_sims-len(st.session_state.fe1000_results)
            this_batch=min(int(batch_size),remaining)
            prog=st.progress(0)
            status=st.empty()
            started=time.perf_counter()

            # Prepare once per click. Every worker receives the same immutable prepared board.
            _sim_board=_prepare_fast_sim_board(board)
            _seed0=int(st.session_state.fe1000_next_seed)

            # Retry prior failed seeds first; successful drafts are preserved.
            _prior_failures=list(st.session_state.get("fe_benchmark_failures",[]))
            _retry_seeds=[]
            for _f in _prior_failures:
                try:
                    _retry_seeds.append(int(_f.get("seed")))
                except Exception:
                    pass
            _retry_seeds=list(dict.fromkeys(_retry_seeds))
            _retry_seeds=_retry_seeds[:this_batch]
            _fresh_needed=max(this_batch-len(_retry_seeds),0)
            _fresh_seeds=list(range(_seed0,_seed0+_fresh_needed))
            _seeds=_retry_seeds+_fresh_seeds

            # Failures being retried are removed now; any seed that fails again will be re-added.
            if _retry_seeds:
                _retry_set=set(_retry_seeds)
                st.session_state.fe_benchmark_failures=[
                    _f for _f in _prior_failures
                    if int(_f.get("seed",-1)) not in _retry_set
                ]

            def _run_one_sim(_seed):
                return _seed,simulate_current_fantasy_edge_once(
                    _sim_board,int(teams),int(slot),int(rounds),
                    state["roster_slots"],int(randomness),int(_seed)
                )

            # The production candidate engine is pandas/numpy heavy and benefits from overlapping
            # independent drafts. Cap workers to avoid overwhelming Streamlit Cloud memory/CPU.
            _workers=1
            _finished=[]
            _errors=[]
            with concurrent.futures.ThreadPoolExecutor(max_workers=_workers) as _pool:
                _future_map={_pool.submit(_run_one_sim,_seed):_seed for _seed in _seeds}
                for _n,_future in enumerate(concurrent.futures.as_completed(_future_map),start=1):
                    _seed=_future_map[_future]
                    try:
                        _seed,result=_future.result()
                        if result is not None:
                            _finished.append((_seed,result))
                        else:
                            _errors.append((_seed,"Simulation returned no result"))
                    except Exception as _exc:
                        _errors.append((_seed,f"{type(_exc).__name__}: {_exc}"))
                    prog.progress(_n/max(this_batch,1))
                    status.caption(
                        f"Finished {_n}/{this_batch} this batch • "
                        f"{len(st.session_state.fe1000_results)+len(_finished):,}/{target_sims:,} total"
                    )

            # Keep deterministic seed/result ordering even though workers finish out of order.
            _finished.sort(key=lambda x:x[0])
            if _errors:
                st.session_state.fe_benchmark_failures.extend(
                    [{"seed":int(_seed),"error":str(_err)} for _seed,_err in _errors]
                )
            for _seed,result in _finished:
                result["simulation"]=len(st.session_state.fe1000_results)+1
                result["seed"]=int(_seed)
                st.session_state.fe1000_results.append(result)

            st.session_state.fe1000_next_seed=_seed0+_fresh_needed
            _elapsed=max(time.perf_counter()-started,0.001)
            st.session_state["fe_last_batch_seconds"]=_elapsed
            st.session_state["fe_last_batch_rate"]=max(len(_finished),1)/_elapsed
            if _errors:
                st.session_state["fe_last_batch_error_count"]=len(_errors)
            else:
                st.session_state.pop("fe_last_batch_error_count",None)
            st.rerun()

        sim_df=pd.DataFrame(st.session_state.fe1000_results)
        if len(sim_df):
            st.markdown("### Simulation results")
            c1,c2,c3,c4=st.columns(4)
            c1.metric("Drafts completed",f"{len(sim_df):,}")
            c2.metric("Average grade",f"{sim_df.grade.mean():.1f}")
            c3.metric("Average Model Edge",f"{sim_df.model_edge.mean():.1f}/100")
            c4.metric("Legal roster rate",f"{sim_df.legal_roster.mean():.1%}")
            if all(c in sim_df.columns for c in ["starter_vorp","harmful_regret_count","champion_score"]):
                q1,q2,q3,q4=st.columns(4)
                q1.metric("Avg Starter VORP",f"{pd.to_numeric(sim_df.starter_vorp,errors='coerce').mean():.1f}")
                q2.metric("Harmful regret / draft",f"{pd.to_numeric(sim_df.harmful_regret_count,errors='coerce').mean():.2f}")
                q3.metric("Major reaches / draft",f"{pd.to_numeric(sim_df.major_reach_count,errors='coerce').mean():.2f}")
                q4.metric("Champion score",f"{pd.to_numeric(sim_df.champion_score,errors='coerce').mean():.1f}")

            d1,d2,d3,d4=st.columns(4)
            d1.metric("Avg RB",f"{sim_df.RB.mean():.2f}")
            d2.metric("Avg WR",f"{sim_df.WR.mean():.2f}")
            d3.metric("Avg IDP",f"{sim_df.IDP_total.mean():.2f}")
            d4.metric("3+ IDP drafts",f"{(sim_df.IDP_total>=3).mean():.1%}")

            st.markdown("#### Construction distribution")
            construction_summary=pd.DataFrame({
                "Metric":[
                    "6+ RB drafts","6+ WR drafts","Only 2 IDPs",
                    "3+ IDPs","4 IDPs","Invalid required roster"
                ],
                "Rate":[
                    float((sim_df.RB>=6).mean()),
                    float((sim_df.WR>=6).mean()),
                    float((sim_df.IDP_total<=2).mean()),
                    float((sim_df.IDP_total>=3).mean()),
                    float((sim_df.IDP_total>=4).mean()),
                    float((~sim_df.legal_roster).mean()),
                ]
            })
            construction_summary["Rate"]=construction_summary["Rate"].map(lambda v:f"{v:.1%}")
            st.dataframe(construction_summary,use_container_width=True,hide_index=True)

            st.markdown("#### Score distribution")
            st.dataframe(
                sim_df[[c for c in ["simulation","grade","model_edge","draft_value","construction",
                        "positional_advantage","opportunity_penalty","starter_vorp","bench_upside",
                        "harmful_regret_count","major_reach_count","champion_score",
                        "RB","WR","DL","DB","IDP_total","legal_roster"] if c in sim_df.columns]]
                .tail(100),
                use_container_width=True,hide_index=True
            )

            if len(sim_df)>=target_sims:
                _cert={
                    "100% legal rosters": bool(sim_df["legal_roster"].fillna(False).all()),
                    "100% production-engine user picks": bool((pd.to_numeric(sim_df["production_engine_usage"],errors="coerce").fillna(0)>=0.999).all()),
                    "0 unavailable-player recommendations": bool((pd.to_numeric(sim_df["unavailable_user_picks"],errors="coerce").fillna(999)==0).all()),
                    "0 duplicate user players": bool((pd.to_numeric(sim_df["duplicate_user_players"],errors="coerce").fillna(999)==0).all()),
                    "Exact configured roster size": bool(
                        (pd.to_numeric(sim_df["roster_size"],errors="coerce").fillna(0) ==
                         pd.to_numeric(sim_df["expected_roster_size"],errors="coerce").fillna(-1)).all()
                    ),
                    "100% TE completion": bool((pd.to_numeric(sim_df["TE"],errors="coerce").fillna(0)>=1).all()),
                    "100% K completion": bool((pd.to_numeric(sim_df["K"],errors="coerce").fillna(0)>=1).all()),
                    "100% DL completion": bool((pd.to_numeric(sim_df["DL"],errors="coerce").fillna(0)>=1).all()),
                    "100% DB completion": bool((pd.to_numeric(sim_df["DB"],errors="coerce").fillna(0)>=1).all()),
                    "0 drafts with 4+ IDPs": bool((pd.to_numeric(sim_df["IDP_total"],errors="coerce").fillna(99)<=3).all()),
                    "0 production-engine exceptions": bool(len(st.session_state.get("fe_benchmark_failures",[]))==0),
                    "Average Construction >= 94": bool(pd.to_numeric(sim_df["construction"],errors="coerce").mean()>=94.0),
                    "Average Opportunity Penalty <= 6": bool(pd.to_numeric(sim_df["opportunity_penalty"],errors="coerce").mean()<=6.0),
                    "Average Draft Value >= 85": bool(pd.to_numeric(sim_df["draft_value"],errors="coerce").mean()>=85.0),
                    "Average Model Edge >= 82": bool(pd.to_numeric(sim_df["model_edge"],errors="coerce").mean()>=82.0),
                    "Average Opportunity Penalty <= 4": bool(pd.to_numeric(sim_df["opportunity_penalty"],errors="coerce").mean()<=4.0),
                    "0 harmful-regret decisions": bool((pd.to_numeric(sim_df.get("harmful_regret_count",0),errors="coerce").fillna(99)==0).all()),
                    "0 major reaches": bool((pd.to_numeric(sim_df.get("major_reach_count",0),errors="coerce").fillna(99)==0).all()),
                    "Average Starter VORP >= 34": bool(pd.to_numeric(sim_df.get("starter_vorp",0),errors="coerce").mean()>=34.0),
                    "No RB7+ rosters": bool((pd.to_numeric(sim_df["RB"],errors="coerce").fillna(99)<=6).all()),
                    "No WR7+ rosters": bool((pd.to_numeric(sim_df["WR"],errors="coerce").fillna(99)<=6).all()),
                }
                st.markdown("### Certification")
                st.dataframe(pd.DataFrame({"Check":list(_cert.keys()),"Pass":list(_cert.values())}),use_container_width=True,hide_index=True)
                if all(_cert.values()):
                    st.success("100-draft certification PASSED. Results are safe to use for tuning.")
                else:
                    st.error("100-draft certification FAILED. Do not tune weights from this run.")

        st.caption(
            "Fantasy Edge simulation tools use the current roster construction, value, timing, "
            "IDP, kicker, reach, and bench-optimization rules above."
        )

with tabs[3]:
    st.subheader("🧲 Roster-Aware Add / Drop Engine")
    st.caption("Every move is simulated against your actual roster, re-optimized through Start / Sit, and scored for both this week and rest-of-season value.")
    st.session_state["_v742_waiver_transactions"]=[]

    _my_roster=board[board["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    _fa=board[board["player"].map(lambda n:_is_free_agent(state,n))].copy()

    if _my_roster.empty:
        st.info("Add your roster under League Setup first.")
    elif _fa.empty:
        st.info("No free agents are currently available in the ownership map.")
    else:
        _base_starters,_base_bench,_base_lineup=_v676_optimize_lineup(_my_roster)
        _base_roster_score=_v678_scores_from_optimized(_base_starters,_base_bench,_base_lineup)

        m1,m2,m3=st.columns(3)
        m1.metric("Current optimized lineup",f"{_base_lineup:.1f} PPG")
        m2.metric("Roster value",f"{_base_roster_score:.1f}")
        m3.metric("Free agents",f"{len(_fa)}")
        # V7.06 diagnostic feed coverage: show exactly which evidence feeds are weak.
        _inj_cov=int(_v683_health.get("injury_coverage",0) or 0)
        _mat_cov=int(_v683_health.get("matchup_coverage",0) or 0)
        _role_cov=int(_v683_health.get("role_coverage",0) or 0)
        _role_current_cov=int(round(100.0*float((board.get("_usage_recency",pd.Series(index=board.index,dtype=str)).astype(str).eq("CURRENT")).mean()))) if len(board) else 0
        _role_hist_cov=int(round(100.0*float((board.get("_usage_recency",pd.Series(index=board.index,dtype=str)).astype(str).eq("PRIOR_SEASON")).mean()))) if len(board) else 0
        _role_conf_cov=int(round(100.0*float((pd.to_numeric(board.get("_role_confidence",pd.Series(0,index=board.index)),errors="coerce").fillna(0)>=60).mean()))) if len(board) else 0
        _team_cov=int(round(100.0*float(pd.to_numeric(board.get("_live_team_verified",0),errors="coerce").fillna(0).mean()))) if len(board) else 0
        _ext_matches=0
        try:
            _wproj=_v692_sleeper_weekly_projections(
                int(_v678_live_week.get("season",datetime.now().year)),
                int(_v678_live_week.get("week",1))
            )
            if isinstance(_wproj,pd.DataFrame) and len(_wproj):
                _board_keys=set(board["player"].map(_owner_key))
                _ext_matches=int(_wproj["_key"].isin(_board_keys).sum()) if "_key" in _wproj.columns else 0
        except Exception:
            _ext_matches=0

        # V7.08: a zero current-season usage rate before Week 1 games have produced
        # player-stat rows is an expected pregame state, not a broken feed. Historical
        # usage remains context-only and cannot create a positive role adjustment.
        _live_season=int(_v678_live_week.get("season",datetime.now().year) or datetime.now().year)
        _live_week=int(_v678_live_week.get("week",1) or 1)
        _current_usage_rows=_v683_weekly_usage_table_current(_live_season)
        _pregame_role_state=(
            _live_week<=1
            and (not isinstance(_current_usage_rows,pd.DataFrame) or _current_usage_rows.empty)
            and _role_hist_cov>0
        )
        _role_label=(
            "Current role/usage: pregame — no current-season game stats yet ✓"
            if _pregame_role_state else
            f"Observed game usage: {_role_current_cov}% • role confidence: {_role_conf_cov}% {'✓' if _role_conf_cov>=70 else '⚠'}"
        )
        _feed_parts=[
            f"Injury: {_inj_cov}% {'✓' if _inj_cov>=70 else '⚠'}",
            f"Live team identity: {_team_cov}% {'✓' if _team_cov>=70 else '⚠'}",
            f"Matchup: {_mat_cov}% {'✓' if _mat_cov>=70 else '⚠'}",
            _role_label,
            f"Historical role fallback: {_role_hist_cov}%",
            f"External projections: {_ext_matches} matched {'✓' if _ext_matches>0 else '⚠'}"
        ]
        _role_bad=(not _pregame_role_state) and (_role_conf_cov<70)
        if _inj_cov<70 or _mat_cov<70 or _team_cov<70 or _role_bad or _ext_matches==0:
            st.warning("Data coverage — "+" • ".join(_feed_parts))
        else:
            st.success("Data coverage — "+" • ".join(_feed_parts))
        st.caption("V7.48 position-need integrity: REQUIRED COVERAGE is reserved for true playable-lineup holes; QUESTIONABLE/news-risk starters create PREP-only contingency watches, and unusable waiver candidates cannot satisfy an emergency.")

        _f1,_f2,_f3=st.columns(3)
        with _f1:
            _add_pos=st.selectbox("Add position",["All","RB","WR","TE","QB","DL","DB","K"],key="v676_add_pos")
        with _f2:
            _min_move=st.selectbox("Show",["All moves","WATCH or better","ADD or better","PRIORITY only"],index=1,key="v676_move_filter")
        with _f3:
            _allow_protected=st.toggle("Allow protected drops",value=False,key="v682_allow_protected_drops",
                                      help="Off protects core players and valuable IR/PUP stashes from appearing as recommended drops.")

        # V7.42: news risk is a provisional contingency signal, never an official status.
        # It is evaluated here so Waivers, not only Command Center, can react immediately.
        _v742_waiver_news=_v742_news_watch(board,state)
        _v742_news_risks=_v742_news_risk_map(_v742_waiver_news)
        _v737_emergency_positions,_v748_prep_positions,_v748_need_reasons=_v748_required_position_need_state(_my_roster,_v742_waiver_news)
        _v737_active_emergencies=(set(_v737_emergency_positions) if _add_pos=="All" else ({_add_pos} & set(_v737_emergency_positions)))
        _v748_active_prep=(set(_v748_prep_positions) if _add_pos=="All" else ({_add_pos} & set(_v748_prep_positions)))
        _v737_selected_emergency=bool(_v737_active_emergencies)

        _fa_eval=_fa.copy()
        if _add_pos!="All":
            _fa_eval=_fa_eval[_fa_eval["position"].eq(_add_pos)]
        elif _v737_active_emergencies:
            # HARD coverage holes take priority over optional/stash moves.
            _fa_eval=_fa_eval[_fa_eval["position"].isin(_v737_active_emergencies)]
        # PREP-only positions do not hijack the All view. They receive a ranking bump
        # later, so a questionable QB cannot suppress a more important TE contingency.
        # V7.39: rank direct backups using the temporary role that opens when a rostered
        # teammate at the same NFL position is unavailable (e.g. TE2 behind an injured TE1).
        # This is week-context only and never rewrites the frozen core projection model.
        _v742_opportunity=_fa_eval.apply(lambda r:_v739_temporary_opportunity(r,_my_roster,_v742_news_risks),axis=1)
        _fa_eval["_v739_opportunity_boost"]=[x[0] for x in _v742_opportunity]
        _fa_eval["_v739_opportunity_reason"]=[x[1] for x in _v742_opportunity]
        _fa_eval["_v748_prep_boost"]=_fa_eval["position"].astype(str).str.upper().map(lambda p:2.5 if p in _v748_active_prep else 0.0)
        _fa_eval["_candidate_value"]=_fa_eval.apply(_v676_player_value,axis=1)+_fa_eval["_v739_opportunity_boost"]+_fa_eval["_v748_prep_boost"]
        if _v737_active_emergencies:
            _fa_eval=_fa_eval[_fa_eval.apply(_v748_immediate_coverage_candidate,axis=1)].copy()
        _fa_eval=_fa_eval.sort_values(["_candidate_value","_v739_opportunity_boost","vorp"],ascending=False).head(35)

        _moves=[]
        _hold_candidates=[]
        _hold_stage_counts={"illegal":0,"precheck":0,"guard":0}
        _drops_all=_my_roster.copy()
        _drops_all["_drop_value"]=_drops_all.apply(_v676_player_value,axis=1)
        _drops_all["_ros_value"]=_drops_all.apply(_v682_ros_value,axis=1)
        _drops_all["_drop_protection"]=_drops_all.apply(_v682_drop_protection,axis=1)
        # V7.45: protection is tiered instead of binary. The old binary label was
        # classifying nearly the entire roster as protected before a transaction could
        # even be compared. Final guards remain authoritative; this only admits
        # CONDITIONAL/DROPPABLE bench assets to transaction scoring.
        _starter_names=set(_base_starters["Player"].astype(str).tolist()) if isinstance(_base_starters,pd.DataFrame) and len(_base_starters) else set()
        _drops_all["_drop_tier"]=_drops_all.apply(lambda r:_v745_drop_tier(r,_starter_names),axis=1)
        if not _allow_protected:
            _eligible_drops=_drops_all[_drops_all["_drop_tier"].isin(["CONDITIONAL","DROPPABLE"])].copy()
        else:
            _eligible_drops=_drops_all[_drops_all["_drop_tier"].ne("LOCKED")].copy()

        if _eligible_drops.empty and not _allow_protected:
            st.info("No conditional or droppable bench assets are available. LOCKED/PROTECTED assets remain excluded.")

        # V7.13: prune by true drop opportunity cost, not depressed weekly projection alone.
        # Required-position emergency override: if the current week has no playable starter
        # at the selected position (e.g. only TE is DOUBTFUL), evaluate the safest non-core
        # bench cuts even when ordinary protection would otherwise produce HOLD.
        if _v737_selected_emergency:
            _emergency_pool=_drops_all.copy()
            _emergency_pool["_drop_cost"]=_emergency_pool.apply(lambda r:_v711_drop_asset_cost(r,_starter_names),axis=1)
            _emergency_pool=_emergency_pool[_emergency_pool.apply(lambda r:any(_v737_emergency_drop_ok(r,_starter_names,p) for p in _v737_active_emergencies),axis=1)].copy()
            if len(_emergency_pool):
                _eligible_drops=pd.concat([_eligible_drops,_emergency_pool],ignore_index=True).drop_duplicates(subset=["player"])
            _emergency_label=", ".join(sorted(_v737_active_emergencies))
            st.warning(f"🚨 REQUIRED POSITION COVERAGE — no safe playable {_emergency_label} is currently available on your roster. Fantasy Edge is evaluating the least-damaging contingency automatically, even while Add position is set to All.")
        if _v748_active_prep:
            _prep_bits=[]
            for _p in sorted(_v748_active_prep):
                _prep_bits.append(f"{_p}: {_v748_need_reasons.get(_p,'starter availability risk')}")
            st.info("👀 CONTINGENCY PREP — roster coverage still exists, so this is not a forced add. " + " • ".join(_prep_bits))

        _eligible_drops["_drop_cost"]=_eligible_drops.apply(lambda r:_v711_drop_asset_cost(r,_starter_names),axis=1)

        # V7.36 FINAL protected-drop execution guard.
        # Protection labels are the first line of defense, but a valuable roster asset
        # must never leak into executable waiver recommendations because stale rank/VORP
        # fields failed to assign a label. Drop Cost is an independent opportunity-cost
        # signal, so protected mode OFF also excludes starters and high-cost assets.
        if not _allow_protected and not _v737_selected_emergency:
            # V7.45: do not re-create the old binary protection bug with a Drop Cost
            # cutoff here. CONDITIONAL assets must reach transaction scoring, where
            # _v711_move_viable and the final V7.14 gate can reject bad swaps.
            _eligible_drops=_eligible_drops[~_eligible_drops["player"].astype(str).isin(_starter_names)].copy()
        elif _v737_selected_emergency:
            _eligible_drops=_eligible_drops[_eligible_drops.apply(lambda r:any(_v737_emergency_drop_ok(r,_starter_names,p) for p in _v737_active_emergencies),axis=1)].copy()

        # V7.38: required-position coverage must rank cuts by roster damage, not raw
        # Drop Cost alone. This prevents an injured-but-valuable RB from becoming the
        # default cut when a surplus bench DL/DB or other expendable depth piece exists.
        if _v737_selected_emergency and len(_eligible_drops):
            _eligible_drops["_emergency_drop_rank"]=_eligible_drops.apply(
                lambda r:min(_v738_emergency_drop_rank(r,_my_roster,_starter_names,p) for p in _v737_active_emergencies),axis=1)
            _eligible_drops=_eligible_drops[_eligible_drops["_emergency_drop_rank"].lt(900)].copy()
            _weak_overall=_eligible_drops.sort_values(["_emergency_drop_rank","_drop_cost","_drop_value","_ros_value"]).head(10)
        else:
            _eligible_drops["_emergency_drop_rank"]=_eligible_drops["_drop_cost"]
            _weak_overall=_eligible_drops.sort_values(["_drop_cost","_drop_value","_ros_value"]).head(8)

        for _,add_raw in _fa_eval.iterrows():
            # V7.39 simulation uses an adjusted COPY. The board/base projection stays frozen.
            add=_v739_apply_temporary_opportunity(add_raw,_my_roster,_v742_news_risks)
            _opp_boost=float(add.get("_v739_opportunity_boost",0) or 0)
            _opp_reason=str(add.get("_v739_opportunity_reason","") or "")
            _opp_source=str(add.get("_v739_opportunity_source","") or "")
            _opp_conf=float(add.get("_v739_opportunity_confidence",0) or 0)
            _need_adj,_need_label=_v703_need_adjustment(add["position"],_my_roster,state)
            _evidence=_v703_evidence_quality(add_raw)
            # V7.39.1: keep Evidence numeric. V7.39 accidentally converted the
            # evidence count to a string when adding temporary-role context, which
            # later crashed _v703_why_not on `evidence <= 1`. Keep the score/count
            # numeric and expose opportunity context in its own display field.
            _evidence_detail=(f"TEMP ROLE +{_opp_boost:.1f}" if _opp_boost>0 else "—")
            if str(add.get("position","")).upper() in _v737_active_emergencies:
                # Do not bias emergency coverage toward same-position cuts; rank the
                # whole roster by least damage. (The injured TE being covered is barred.)
                _drop_pool=_eligible_drops[_eligible_drops.apply(lambda r:_v737_emergency_drop_ok(r,_starter_names,add.get("position","")),axis=1)].copy()
                _drop_pool["_emergency_drop_rank"]=_drop_pool.apply(lambda r:_v738_emergency_drop_rank(r,_my_roster,_starter_names,add.get("position","")),axis=1)
                _drop_pool=_drop_pool[_drop_pool["_emergency_drop_rank"].lt(900)].sort_values(["_emergency_drop_rank","_drop_cost","_drop_value","_ros_value"]).head(10)
            else:
                _same_pos=_eligible_drops[_eligible_drops["position"].eq(add["position"])].sort_values(["_drop_cost","_drop_value","_ros_value"]).head(4)
                _drop_pool=pd.concat([_weak_overall,_same_pos],ignore_index=True)
                _drop_pool=_drop_pool.drop_duplicates(subset=["player"]).head(10)

            for _,drop in _drop_pool.iterrows():
                if not _v676_legal_drop(_my_roster,drop,add):
                    _hold_stage_counts["illegal"]+=1
                    continue

                # Fast precheck: if add is clearly worse than drop and cannot touch the lineup,
                # skip the expensive full simulation.
                add_val=_v676_player_value(add)
                drop_val=_v676_player_value(drop)
                if add_val + 0.35 < drop_val and add["position"]==drop["position"]:
                    _hold_stage_counts["precheck"]+=1
                    _hold_candidates.append({
                        "Add":str(add.get("player","")),"Pos":str(add.get("position","")),
                        "Drop":str(drop.get("player","")),"Drop Pos":str(drop.get("position","")),
                        "Net Week":0.0,"Net ROS":round(float(_v682_ros_value(add_raw)-_v682_ros_value(drop)),2),
                        "Drop Cost":round(float(_v711_drop_asset_cost(drop,_starter_names)),2),
                        "Add Strength":round(float(_v712_add_asset_strength(add)),2),
                        "Role Confidence":round(float(_v682_num(add,"_role_confidence",0)),1),
                        "Role Source":str(add.get("_role_confidence_source","") or "—"),
                        "Veto":f"Fast precheck: add value {add_val:.2f} trails same-position drop {drop_val:.2f}"
                    })
                    continue

                sim=_my_roster[_my_roster["player"].ne(drop["player"])].copy()
                sim=pd.concat([sim,pd.DataFrame([add])],ignore_index=True)
                _sim_starters,_sim_bench,new_lineup=_v676_optimize_lineup(sim)
                new_roster=_v678_scores_from_optimized(_sim_starters,_sim_bench,new_lineup)
                net_lineup=new_lineup-_base_lineup
                net_roster=new_roster-_base_roster_score
                # Temporary injury opportunity is primarily a weekly edge, not permanent ROS value.
                add_ros=_v682_ros_value(add_raw) + (_opp_boost*0.20)
                drop_ros=_v682_ros_value(drop)
                net_ros=add_ros-drop_ros
                _is_emergency_move=(str(add.get("position","")).upper() in _v737_emergency_positions)
                if _is_emergency_move and _v737_emergency_drop_ok(drop,_starter_names,add.get("position","")):
                    # V7.46: emergency need relaxes position coverage, never asset value.
                    _viable,_hold_reason,_drop_cost=_v746_emergency_asset_ok(add,drop,net_lineup,net_ros,_starter_names)
                else:
                    _viable,_hold_reason,_drop_cost=_v711_move_viable(add,drop,net_lineup,net_ros,_need_label,_starter_names)
                if not _viable:
                    _hold_stage_counts["guard"]+=1
                    _hold_candidates.append({
                        "Add":str(add.get("player","")),"Pos":str(add.get("position","")),
                        "Drop":str(drop.get("player","")),"Drop Pos":str(drop.get("position","")),
                        "Net Week":round(float(net_lineup),2),"Net ROS":round(float(net_ros),2),
                        "Drop Cost":round(float(_drop_cost),2),
                        "Add Strength":round(float(_v712_add_asset_strength(add)),2),
                        "Role Confidence":round(float(_v682_num(add,"_role_confidence",0)),1),
                        "Role Source":str(add.get("_role_confidence_source","") or "—"),
                        "Veto":str(_hold_reason or "Transaction guard")
                    })
                    continue
                action=("🚨 ADD FOR COVERAGE" if _is_emergency_move else _v682_move_action(net_lineup,net_ros,add))
                _moves.append({
                    "Add":add["player"],"Pos":add["position"],
                    "Add Status":_v677_status_icon(add.get("injury","")),
                    "Add Practice":_v680_practice_risk(add.get("practice_status","")),
                    "Add Injury":str(add.get("injury_detail","") or "—"),
                    "Add Matchup":str(add.get("_opponent","—"))+" "+str(add.get("_matchup_grade","—")),
                    "Drop":drop["player"],"Drop Pos":drop["position"],
                    "Drop Status":_v677_status_icon(drop.get("injury","")),
                    "Drop Practice":_v680_practice_risk(drop.get("practice_status","")),
                    "Drop Protection":_v682_drop_protection(drop),
                    "Drop Cost":_drop_cost,
                    "Emergency Drop Rank":round(float(drop.get("_emergency_drop_rank",_drop_cost)),2),
                    "Drop Context":(
                        f"IR until Week {_v740_reserve_return_week(drop)}" if _v740_reserve_return_week(drop)>0
                        else ("OUT this week" if _v677_normalize_injury_status(drop.get("injury_effective",drop.get("injury","")))=="OUT"
                              else ("DOUBTFUL" if _v677_normalize_injury_status(drop.get("injury_effective",drop.get("injury","")))=="DOUBTFUL" else "Active/bench"))
                    ),
                    "Drop Tier":_v745_drop_tier(drop,_starter_names),
                    "Why This Drop":_v746_drop_explanation(drop,_my_roster,_starter_names,add.get("position","") if _is_emergency_move else ""),
                    "Net Week":round(net_lineup,2),"Net Roster":round(net_roster,2),
                    "Net ROS":round(net_ros,2),
                    "Add PPG":round(float(pd.to_numeric(pd.Series([add_raw.get("projection",0)]),errors="coerce").fillna(0).iloc[0]),2),
                    "Effective Add PPG":round(float(pd.to_numeric(pd.Series([add.get("projection",0)]),errors="coerce").fillna(0).iloc[0]),2),
                    "Opportunity Boost":round(_opp_boost,2),
                    "Opportunity":(_opp_reason if _opp_reason else "—"),
                    "Opportunity Confidence":round(_opp_conf,2) if _opp_boost>0 else 0.0,
                    "Drop PPG":round(float(pd.to_numeric(pd.Series([drop.get("projection",0)]),errors="coerce").fillna(0).iloc[0]),2),
                    "Add ROS":round(add_ros,2),"Drop ROS":round(drop_ros,2),
                    "Add Role":_v683_role_summary(add),
                    "Drop Role":_v683_role_summary(drop),
                    "Add Recent PPG":round(_v682_num(add,"_recent_ppg3",0),2),
                    "Drop Recent PPG":round(_v682_num(drop,"_recent_ppg3",0),2),
                    "Add VORP":round(float(pd.to_numeric(pd.Series([add.get("vorp",0)]),errors="coerce").fillna(0).iloc[0]),2),
                    "Drop VORP":round(float(pd.to_numeric(pd.Series([drop.get("vorp",0)]),errors="coerce").fillna(0).iloc[0]),2),
                    "Action":action,
                    "Emergency Coverage":bool(_is_emergency_move),
                    "Need Adj":_need_adj,"Need Fit":("REQUIRED POSITION CONTINGENCY" if _is_emergency_move else ("CONTINGENCY WATCH" if str(add.get("position","")).upper() in _v748_active_prep else _need_label)),"Evidence":int(_evidence),
                    "Evidence Detail":_evidence_detail,
                    "Move Type":_v703_move_type(net_lineup,net_ros),
                    "Why":_v682_move_reason(net_lineup,net_ros,add,drop)
                })

        _moves_df=pd.DataFrame(_moves)
        if _moves_df.empty:
            st.info("HOLD — no worthwhile add/drop transaction clears the roster-asset guard right now.")
            if _hold_candidates:
                _hd=pd.DataFrame(_hold_candidates)
                _hd["_near_score"]=(pd.to_numeric(_hd["Net Week"],errors="coerce").fillna(0)*8.0 + pd.to_numeric(_hd["Net ROS"],errors="coerce").fillna(0)*4.0 - pd.to_numeric(_hd["Drop Cost"],errors="coerce").fillna(0)*0.12)
                _hd=_hd.sort_values(["_near_score","Net Week","Net ROS"],ascending=False).drop(columns="_near_score").head(5)
                _best=_hd.iloc[0]
                st.caption(f"Closest rejected move: add {_best['Add']} / drop {_best['Drop']} • Week {_best['Net Week']:+.2f} • ROS {_best['Net ROS']:+.2f} • drop cost {_best['Drop Cost']:.1f} • {_best['Veto']}")
                with st.expander("Why Fantasy Edge is holding"):
                    st.dataframe(_hd,use_container_width=True,hide_index=True)
                    st.caption(f"Evaluated rejections — guard: {_hold_stage_counts['guard']} • fast precheck: {_hold_stage_counts['precheck']} • illegal pairs: {_hold_stage_counts['illegal']}")
            else:
                _reason=("No CONDITIONAL or DROPPABLE bench candidates remain after contextual protection." if len(_eligible_drops)==0 else "No legal add/drop pair reached transaction scoring after candidate filtering.")
                st.caption("HOLD diagnostic: "+_reason)
        else:
            _ps=[]; _pl=[]
            for _,_wr in _moves_df.iterrows():
                _ar=board[board["player"].eq(_wr["Add"])]
                _dr=board[board["player"].eq(_wr["Drop"])]
                if len(_ar) and len(_dr): _sc,_lab=_v697_waiver_priority_score(_ar.iloc[0],_dr.iloc[0],state,_wr["Net Week"],_wr["Net ROS"],_wr["Net Roster"],_wr["Need Adj"])
                else: _sc,_lab=0.0,"⛔ PASS"
                _dc=float(_wr.get("Drop Cost",0) or 0)
                # High opportunity-cost drops reduce urgency even when raw weekly values are noisy.
                _sc=max(0.0,round(float(_sc)-max(0.0,_dc-35.0)*0.22,1))
                if _dc>=55 and float(_wr.get("Net Week",0))<0.75 and float(_wr.get("Net ROS",0))<2.25:
                    _lab="👀 WATCH" if _sc>=50 else "⛔ PASS"
                _ps.append(_sc); _pl.append(_lab)
            _moves_df["Priority Score"]=_ps; _moves_df["Waiver Call"]=_pl

            # V7.41 Contextual Decision Engine. Rank close choices by fit for the actual
            # roster problem (for example, a short-term TE replacement), without changing
            # any base projection, VORP, ROS model, or the legal-drop guards.
            _best_eff_by_pos={}
            if len(_moves_df):
                for _p,_g in _moves_df.groupby("Pos"):
                    _best_eff_by_pos[str(_p)]=float(pd.to_numeric(_g["Effective Add PPG"],errors="coerce").fillna(0).max())
            _ctx=[]
            for _,_r in _moves_df.iterrows():
                _ctx.append(_v741_contextual_waiver_score(_r,_best_eff_by_pos.get(str(_r.get("Pos","")),0.0)))
            _moves_df["Decision Score"]=[x[0] for x in _ctx]
            _moves_df["Context Fit"]=[x[1] for x in _ctx]
            _moves_df["Decision Why"]=[x[2] for x in _ctx]
            _moves_df["Transaction Score"]=_moves_df.apply(_v742_transaction_score,axis=1)

            if "Emergency Coverage" in _moves_df.columns:
                _mask=_moves_df["Emergency Coverage"].fillna(False).astype(bool)
                _moves_df.loc[_mask,"Priority Score"]=_moves_df.loc[_mask,"Priority Score"].clip(lower=72.0)
                _moves_df.loc[_mask,"Waiver Call"]="🚨 REQUIRED COVERAGE"
            _budget_claim=_moves_df.apply(lambda r:_v703_faab_guidance(r["Priority Score"],r["Waiver Call"],state),axis=1)
            _moves_df["FAAB"]=[x[0] for x in _budget_claim]
            _moves_df["Claim Advice"]=[x[1] for x in _budget_claim]
            _moves_df["Why Not Priority"]=_moves_df.apply(lambda r:_v703_why_not(r["Waiver Call"],r["Net Week"],r["Net ROS"],r["Need Fit"],r["Evidence"]),axis=1)

            # V7.14 FINAL OUTPUT HARD SAFETY GATE.  This is deliberately after priority tiering
            # and immediately before rows can reach the rendered recommendation table.
            # It prevents any earlier fallback/scoring path from re-admitting a bad swap.
            _moves_df=_moves_df[_moves_df.apply(lambda r: bool(r.get("Emergency Coverage",False)) or _v714_final_transaction_ok(r),axis=1)].copy()

            # V7.37 emergency rows bypass the ordinary HOLD gate, but only after passing
            # _v737_emergency_drop_ok. Non-emergency rows retain the frozen V7.14 guard.
            # V7.36 second/final invariant at render boundary. Even if an upstream
            # protection label is stale, protected mode OFF cannot display a transaction
            # that drops a starter or an asset with Drop Cost >= 20.
            if not _allow_protected and len(_moves_df):
                _em=_moves_df.get("Emergency Coverage",pd.Series(False,index=_moves_df.index)).fillna(False).astype(bool)
                _tier_map={_owner_key(r.get("player","")):str(r.get("_drop_tier","LOCKED")) for _,r in _drops_all.iterrows()}
                _normal_ok=_moves_df["Drop"].map(lambda n:_tier_map.get(_owner_key(n),"LOCKED") in ("CONDITIONAL","DROPPABLE")) & ~_moves_df["Drop"].astype(str).isin(_starter_names)
                _moves_df=_moves_df[_em | _normal_ok].copy()

            _call_rank={"🚨 REQUIRED COVERAGE":6,"🔥 PRIORITY CLAIM":5,"⬆️ ADD NOW":4,"🧳 STASH":3,"🎯 STREAMER":2,"👀 WATCH":1,"⛔ PASS":0}
            _moves_df["_call_rank"]=_moves_df["Waiver Call"].map(_call_rank).fillna(0)
            # V7.38: for emergency coverage, least-damaging cut is the first ordering
            # key. For ordinary waivers retain the existing priority ordering.
            if "Emergency Coverage" in _moves_df.columns and _moves_df["Emergency Coverage"].fillna(False).any():
                _moves_df=_moves_df.sort_values(["Emergency Drop Rank","Transaction Score","Decision Score","Priority Score"],ascending=[True,False,False,False])
            else:
                _moves_df=_moves_df.sort_values(["Priority Score","Net Week","Net ROS","Net Roster"],ascending=False)
            _best=_moves_df.groupby("Add",as_index=False,sort=False).head(1).copy()
            if _min_move=="WATCH or better": _best=_best[_best["_call_rank"]>=1]
            elif _min_move=="ADD or better": _best=_best[_best["_call_rank"]>=4]
            elif _min_move=="PRIORITY only": _best=_best[_best["_call_rank"]>=5]

            st.markdown("### Best moves for your roster")
            if _best.empty:
                st.success("🛡️ HOLD — No worthwhile add/drop transaction clears the roster-asset guard right now.")
                st.caption("Your available adds do not create enough immediate lineup value to justify the opportunity cost of the required drop. Protected/reserve assets and valuable starters remain intact.")
            else:
                if "Emergency Coverage" in _best.columns and _best["Emergency Coverage"].fillna(False).any():
                    _best=_best.sort_values(["Transaction Score","Decision Score","Emergency Drop Rank","Priority Score"],ascending=[False,False,True,False])
                else:
                    _best=_best.sort_values(["Priority Score","Net Week","Net ROS"],ascending=False)
                # Command Center and future action surfaces consume this exact ranked result.
                st.session_state["_v742_waiver_transactions"]=_best.head(40).to_dict("records")
                _opp_count=int(pd.to_numeric(_best.get("Opportunity Boost",0),errors="coerce").fillna(0).gt(0).sum()) if len(_best) else 0
                if _opp_count:
                    st.info(f"📈 Temporary opportunity detected for {_opp_count} waiver candidate(s). These weekly boosts automatically disappear when the injured teammate becomes playable again.")
                _ctx_best=_best[_best.get("Context Fit",pd.Series("",index=_best.index)).astype(str).str.contains("BEST CONTEXT FIT",na=False)] if len(_best) else pd.DataFrame()
                if len(_ctx_best):
                    _r=_ctx_best.sort_values("Decision Score",ascending=False).iloc[0]
                    st.success(f"🧠 Context pick: {_r['Add']} — {_r['Decision Why']} (Decision Score {_r['Decision Score']}/100).")
                st.dataframe(_best[["Add","Pos","Drop","Drop Pos","Transaction Score","Decision Score","Context Fit","Decision Why","Drop Cost","Emergency Drop Rank","Drop Tier","Why This Drop","Drop Context","Priority Score","Waiver Call","FAAB","Claim Advice","Move Type","Need Fit","Evidence","Evidence Detail","Opportunity Boost","Effective Add PPG","Opportunity","Opportunity Confidence","Why Not Priority","Net Week","Net ROS","Add Role","Add Recent PPG","Add Status","Add Practice","Add Injury","Add Matchup","Drop Protection","Drop Status","Drop Practice","Drop Role","Drop Recent PPG","Add PPG","Drop PPG","Add ROS","Drop ROS","Add VORP","Drop VORP","Why"]].head(40),
                             use_container_width=True,hide_index=True)

            st.markdown("### 🔒 Drop protection")
            _protect_show=_drops_all[["player","position","team","injury","_drop_tier","_drop_protection","_ros_value"]].copy()
            if len(_protect_show):
                _protect_show["_ros_value"]=_protect_show["_ros_value"].round(2)
                st.dataframe(
                    _protect_show.rename(columns={
                        "player":"Player","position":"Pos","team":"Team","injury":"Status",
                        "_drop_tier":"Tier","_drop_protection":"Protection","_ros_value":"ROS Value"
                    }),
                    use_container_width=True,hide_index=True
                )
            else:
                st.caption("No roster players currently require special drop protection.")

            with st.expander("How to read the move scores"):
                st.write("**Net Week** is the change to your optimized starting lineup this week. **Net ROS** compares long-term Fantasy Edge value of the add versus the drop. **Drop Cost** measures the opportunity cost of cutting that roster asset using starter status, market rank, ROS value, VORP and position. **Why This Drop** audits why the engine believes that specific player is the least-damaging cut. High-cost assets are rejected for stash/luxury moves unless the add creates a clear lineup or major ROS gain.")

        st.caption("V7.03 adds roster need, FAAB/claim guidance, move horizon, evidence gating and why-not explanations. The engine does not execute roster moves.")

with tabs[4]:
    st.subheader("🛡️ Defensive Lineman & Defensive Back board")
    st.caption("DL emphasizes sacks/pressure plus tackle volume. DB emphasizes tackle floor plus interceptions/pass breakups, while discounting unsustainable big-play spikes.")
    x=board[board["position"].isin(["DL","DB"]) & board["player"].map(lambda n:_is_free_agent(state,n))].copy()
    idppos=st.radio("IDP position",["Both","DL","DB"],horizontal=True)
    if idppos!="Both": x=x[x["position"].eq(idppos)]
    x["Breakout"]=x["breakout"].map(lambda v:f"{float(v):.0%}")
    x["Regression"]=x["decline"].map(lambda v:f"{float(v):.0%}")
    st.dataframe(x[["player","position","raw_position","team","projection","vorp","Breakout","Regression","injury","draft_score"]].head(80),
                 use_container_width=True,hide_index=True)


@st.cache_data(ttl=86400, show_spinner=False)
def _v673_2025_ppg_baseline():
    """Robust real 2025 PPG baseline.

    Primary:
      - FantasyPros 2025 PPR FPTS/G for QB/RB/WR/TE
      - FantasyPros 2025 published IDP FPTS/G for DL/DB

    Fallback for offense:
      - nflverse 2025 regular-season player summary
      - fantasy_points_ppr / games

    Returns a DataFrame with player, position, last_ppg, history_source.
    No fake historical values are created.
    """
    import pandas as pd
    import re as _re
    from io import StringIO
    import requests

    rows=[]
    offense={"QB","RB","WR","TE"}

    urls = {
        "QB":"https://www.fantasypros.com/nfl/stats/qb.php?year=2025&scoring=PPR&range=full",
        "RB":"https://www.fantasypros.com/nfl/stats/rb.php?year=2025&scoring=PPR&range=full",
        "WR":"https://www.fantasypros.com/nfl/stats/wr.php?year=2025&scoring=PPR&range=full",
        "TE":"https://www.fantasypros.com/nfl/stats/te.php?year=2025&scoring=PPR&range=full",
        "DL":"https://www.fantasypros.com/nfl/stats/dl.php?year=2025&range=full",
        "DB":"https://www.fantasypros.com/nfl/stats/db.php?year=2025&range=full",
    }

    headers={
        "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131 Safari/537.36",
        "Accept-Language":"en-US,en;q=0.9",
    }

    loaded_positions=set()

    # Primary FantasyPros loader with an explicit browser-style request.
    for pos,url in urls.items():
        try:
            resp=requests.get(url,headers=headers,timeout=12)
            resp.raise_for_status()
            tables=pd.read_html(StringIO(resp.text))
        except Exception:
            continue

        found=False
        for df in tables:
            if isinstance(df.columns,pd.MultiIndex):
                df.columns=[" ".join([str(x) for x in c if str(x)!="nan"]).strip() for c in df.columns]

            player_col=next((c for c in df.columns if str(c).strip().lower()=="player"),None)
            ppg_col=next((c for c in df.columns if "FPTS/G" in str(c).upper()),None)
            if player_col is None or ppg_col is None:
                continue

            added=0
            for _,r in df[[player_col,ppg_col]].iterrows():
                raw=str(r[player_col]).strip()
                ppg=pd.to_numeric(r[ppg_col],errors="coerce")
                if not raw or pd.isna(ppg):
                    continue
                name=_re.sub(r"\s*\([A-Z]{2,3}\)\s*$","",raw).strip()
                if not name:
                    continue
                rows.append({
                    "player":name,
                    "position":pos,
                    "last_ppg":float(ppg),
                    "history_source":"FantasyPros 2025"
                })
                added+=1

            if added:
                loaded_positions.add(pos)
                found=True
                break

    # Offense fallback: nflverse season summary. This is independent of
    # FantasyPros HTML/table parsing and substantially improves veteran coverage.
    missing_offense=offense-loaded_positions
    if missing_offense:
        try:
            nfl_url="https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_2025.csv"
            nf=pd.read_csv(nfl_url)
            name_col=next((c for c in ["player_display_name","player_name","player"] if c in nf.columns),None)
            pos_col=next((c for c in ["position","position_group"] if c in nf.columns),None)
            games_col=next((c for c in ["games","games_played"] if c in nf.columns),None)
            ppr_col=next((c for c in ["fantasy_points_ppr","fantasy_points_ppr_player"] if c in nf.columns),None)

            if name_col and pos_col and games_col and ppr_col:
                nf[pos_col]=nf[pos_col].astype(str).str.upper()
                nf[games_col]=pd.to_numeric(nf[games_col],errors="coerce")
                nf[ppr_col]=pd.to_numeric(nf[ppr_col],errors="coerce")
                nf=nf[nf[pos_col].isin(missing_offense)].copy()
                nf=nf[(nf[games_col]>0) & nf[ppr_col].notna()]

                for _,r in nf.iterrows():
                    rows.append({
                        "player":str(r[name_col]).strip(),
                        "position":str(r[pos_col]).upper(),
                        "last_ppg":float(r[ppr_col])/float(r[games_col]),
                        "history_source":"nflverse 2025 PPR"
                    })
        except Exception:
            pass

    if not rows:
        return pd.DataFrame(columns=["player","position","last_ppg","history_source"])

    out=pd.DataFrame(rows)

    # Prefer FantasyPros if both sources contain the same player/position.
    out["_priority"]=out["history_source"].map({"FantasyPros 2025":0,"nflverse 2025 PPR":1}).fillna(9)
    out["_key"]=out["player"].astype(str).str.lower().str.replace(r"[^a-z0-9]","",regex=True)
    out=out.sort_values("_priority").drop_duplicates(["_key","position"],keep="first")
    return out.drop(columns=["_priority","_key"],errors="ignore")

with tabs[5]:
    st.markdown("## 🚀 Breakout / Regression")
    st.caption("Actionable trend signals built from Fantasy Edge projections, progression/regression inputs, VORP, market value and live league ownership. Scores are model signals — not literal probabilities.")

    # V6.68 automatic refresh. This is polling-based because the public injury
    # directory does not push events directly into Streamlit.
    try:
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
            setTimeout(function () {
                window.parent.location.reload();
            }, 1800000);
            </script>
            """,
            height=0,
            width=0,
        )
    except Exception:
        pass

    _refresh_col1,_refresh_col2,_refresh_col3=st.columns([1.2,1,2.8])
    with _refresh_col1:
        st.caption("🔄 Auto refresh: ON")
    with _refresh_col2:
        if st.button("Refresh now",key="v668_refresh_trends",use_container_width=True):
            try:
                sleeper_players.clear()
            except Exception:
                pass
            for _fn in [_v681_sleeper_injury_watch,_v680_espn_injury_watch_feed,_v680_injury_watch_feed,_v679_espn_roster_status,_v683_weekly_usage_table]:
                try: _fn.clear()
                except Exception: pass
            st.rerun()
    with _refresh_col3:
        st.caption("Injury/status: every 30 min • projection/market sources: 6–24 hr cache • trend scores recalculate every render")

    _trend=board.copy()

    # Repair stale/generic team labels from the active NFL roster directory when available.
    # This directory is identity/status only and never manufactures fantasy value.
    try:
        _active_dir=_v633_active_roster_directory(sleeper_players())
        if not _active_dir.empty:
            _team_map=dict(zip(_active_dir["key"].astype(str),_active_dir["team"].astype(str)))
            _active_map=dict(zip(_active_dir["key"].astype(str),_active_dir["active"].astype(bool)))
            _inj_map=dict(zip(_active_dir["key"].astype(str),_active_dir["injury_status"].astype(str)))
            _trend["_identity_key"]=_trend["player"].map(norm)
            _trend["_active_team"]=_trend["_identity_key"].map(_team_map)
            _has_live_team=_trend["_active_team"].notna() & ~_trend["_active_team"].astype(str).str.upper().isin(["","NFL","FA","NONE","N/A","NAN"])
            _trend.loc[_has_live_team,"team"]=_trend.loc[_has_live_team,"_active_team"]
            _trend["_active_roster"]=_trend["_identity_key"].map(_active_map).fillna(False)
            if "injury" not in _trend.columns:
                _trend["injury"]=""
            _trend["_live_injury"]=_trend["_identity_key"].map(_inj_map).fillna("")
            _trend["injury"]=_trend["injury"].fillna("").astype(str)
            _trend.loc[_trend["injury"].eq(""),"injury"]=_trend.loc[_trend["injury"].eq(""),"_live_injury"]

            _inj_snapshot={k:v for k,v in _inj_map.items() if str(v).strip()}
            _prev_snapshot=st.session_state.get("_v668_injury_snapshot")
            if isinstance(_prev_snapshot,dict):
                _changed=[]
                for _k in set(_prev_snapshot)|set(_inj_snapshot):
                    _old=str(_prev_snapshot.get(_k,"") or "")
                    _new=str(_inj_snapshot.get(_k,"") or "")
                    if _old!=_new:
                        _changed.append((_k,_old,_new))
                if _changed:
                    st.warning(
                        f"🚑 {len(_changed)} NFL injury/status change(s) detected since the last automatic check. "
                        "Breakout, regression and waiver scores have been recalculated."
                    )
            st.session_state["_v668_injury_snapshot"]=_inj_snapshot
        else:
            _trend["_active_roster"]=True
    except Exception:
        # Offline mode still uses the conservative fantasy-relevance gates below.
        _trend["_active_roster"]=True

    _own_state=state.get("ownership",{}) if isinstance(state,dict) else {}
    _team_names=state.get("team_names",{}) if isinstance(state,dict) else {}

    def _trend_owner(player):
        k=_owner_key(player)
        rec=_own_state.get(k)
        if not isinstance(rec,dict):
            return "FREE AGENT"
        owner=str(rec.get("owner","FA"))
        if owner in ("FA","","None"):
            return "FREE AGENT"
        if owner=="ROSTERED_UNKNOWN":
            return "TEAM UNKNOWN"
        return _team_names.get(owner,f"Team {owner}")

    _trend["owner"]=_trend["player"].map(_trend_owner)
    for c in ["projection","vorp","progression","regression","market_pick","model_rank","consensus_rank"]:
        if c in _trend.columns:
            _trend[c]=pd.to_numeric(_trend[c],errors="coerce")

    if "vorp" not in _trend.columns:
        _trend["vorp"]=0.0
    if "progression" not in _trend.columns:
        _trend["progression"]=50.0
    if "regression" not in _trend.columns:
        _trend["regression"]=50.0

    # V6.71: real 2025 PPG baseline from FantasyPros.
    # Offense = 2025 PPR FPTS/G. IDP = FantasyPros 2025 IDP FPTS/G.
    # This replaces the old placeholder-zero history.
    try:
        _hist=_v673_2025_ppg_baseline()
    except Exception:
        _hist=pd.DataFrame()

    _trend["last_ppg"]=pd.NA
    _trend["history_source"]=""

    if isinstance(_hist,pd.DataFrame) and not _hist.empty:
        _hist=_hist.copy()
        _hist["_hist_key"]=_hist["player"].map(norm)
        _hist["_hist_pos"]=_hist["position"].astype(str).str.upper()

        def _v672_aliases(name):
            raw=str(name or "").strip()
            aliases=set()
            base=norm(raw)
            if base:
                aliases.add(base)
            compact=re.sub(r"[^a-z0-9]","",raw.lower())
            if compact:
                aliases.add(compact)
            swaps={
                "kenwalker":"kennethwalker",
                "kennethwalker":"kenwalker",
                "gabedavis":"gabrieldavis",
                "gabrieldavis":"gabedavis",
            }
            for a in list(aliases):
                if a in swaps:
                    aliases.add(swaps[a])
            return aliases

        _hist_map={}
        for _,r in _hist.dropna(subset=["last_ppg"]).iterrows():
            _pos=str(r["_hist_pos"]).upper()
            for _k in _v672_aliases(r["player"]):
                _hist_map[(_k,_pos)]=float(r["last_ppg"])

        def _v672_hist_lookup(player,pos):
            _pos=str(pos).upper()
            for _k in _v672_aliases(player):
                if (_k,_pos) in _hist_map:
                    return _hist_map[(_k,_pos)]
            return pd.NA

        # Build a parallel source map so every historical value is auditable.
        _hist_source_map={}
        for _,r in _hist.dropna(subset=["last_ppg"]).iterrows():
            _pos=str(r["_hist_pos"]).upper()
            _src=str(r.get("history_source","FantasyPros 2025"))
            for _k in _v672_aliases(r["player"]):
                _hist_source_map[(_k,_pos)]=_src

        def _v673_hist_lookup_with_source(player,pos):
            _pos=str(pos).upper()
            for _k in _v672_aliases(player):
                if (_k,_pos) in _hist_map:
                    return _hist_map[(_k,_pos)],_hist_source_map.get((_k,_pos),"2025 history")
            return pd.NA,""

        _hist_pairs=[
            _v673_hist_lookup_with_source(p,pos)
            for p,pos in zip(_trend["player"],_trend["position"])
        ]
        _trend["last_ppg"]=[x[0] for x in _hist_pairs]
        _trend["history_source"]=[x[1] for x in _hist_pairs]

    _trend["last_ppg"]=pd.to_numeric(_trend["last_ppg"],errors="coerce")
    _trend["ppg_change"]=(_trend["projection"]-_trend["last_ppg"]).round(2)
    _has_real_history=_trend["last_ppg"].notna().any()
    _history_col="last_ppg" if _has_real_history else None
    _history_label="2025 PPG" if _has_real_history else None

    # Market/model gap: positive means Fantasy Edge likes the player more than the market.
    if "market_pick" in _trend.columns and "model_rank" in _trend.columns:
        _trend["value_gap"]=(_trend["market_pick"]-_trend["model_rank"]).fillna(0)
    elif "consensus_rank" in _trend.columns and "model_rank" in _trend.columns:
        _trend["value_gap"]=(_trend["consensus_rank"]-_trend["model_rank"]).fillna(0)
    else:
        _trend["value_gap"]=0.0

    # Normalize the existing engine signals into clean 0-100 ranks within position.
    _trend["prog_pct"]=_trend.groupby("position")["progression"].rank(pct=True).fillna(.5)
    _trend["reg_pct"]=_trend.groupby("position")["regression"].rank(pct=True).fillna(.5)
    _trend["proj_pct"]=_trend.groupby("position")["projection"].rank(pct=True).fillna(.5)
    _trend["vorp_pct"]=_trend.groupby("position")["vorp"].rank(pct=True).fillna(.5)
    _trend["value_pct"]=_trend.groupby("position")["value_gap"].rank(pct=True).fillna(.5)

    # If historical PPG exists, growth gets real weight. Otherwise progression is the growth proxy.
    if _history_col:
        _trend["growth_pct"]=_trend.groupby("position")["ppg_change"].rank(pct=True).fillna(.5)
    else:
        _trend["growth_pct"]=_trend["prog_pct"]

    _trend["breakout_score"]=(
        100*(.34*_trend["growth_pct"]+
             .26*_trend["prog_pct"]+
             .18*_trend["value_pct"]+
             .12*_trend["proj_pct"]+
             .10*_trend["vorp_pct"])
    ).clip(0,100).round().astype(int)

    _trend["regression_score"]=(
        100*(.38*_trend["reg_pct"]+
             .24*(1-_trend["growth_pct"])+
             .18*(1-_trend["value_pct"])+
             .12*(1-_trend["proj_pct"])+
             .08*(1-_trend["vorp_pct"]))
    ).clip(0,100).round().astype(int)

    def _break_reason(r):
        x=[]
        if _history_col and pd.notna(r.get("ppg_change")) and r["ppg_change"]>=2: x.append("↑ projected PPG")
        if r.get("progression",50)>=65: x.append("strong progression profile")
        if r.get("value_gap",0)>=15: x.append("model ahead of market")
        if r.get("vorp",0)>0: x.append("positive VORP")
        if r.get("owner")=="FREE AGENT": x.append("available now")
        return " • ".join(x[:3]) or "positive multi-factor trend"

    def _reg_reason(r):
        x=[]
        if _history_col and pd.notna(r.get("ppg_change")) and r["ppg_change"]<=-2: x.append("↓ projected PPG")
        if r.get("regression",50)>=65: x.append("elevated regression profile")
        if r.get("value_gap",0)<=-15: x.append("market ahead of model")
        if r.get("vorp",0)<0: x.append("negative VORP")
        if r.get("owner") not in ("FREE AGENT","TEAM UNKNOWN"): x.append(f"rostered: {r.get('owner')}")
        return " • ".join(x[:3]) or "downside vs positional peers"

    _trend["why_breakout"]=_trend.apply(_break_reason,axis=1)
    _trend["why_regression"]=_trend.apply(_reg_reason,axis=1)

    # V6.62: relevance FIRST, then breakout/regression.
    # A player must matter in fantasy before we care whether he is trending up/down.
    _trend=_trend[_trend["position"].astype(str)!="K"].copy()

    _trend["_market"]=pd.to_numeric(_trend.get("market_pick",999),errors="coerce").fillna(999.0)
    _trend["_rank"]=pd.to_numeric(_trend.get("model_rank",999),errors="coerce").fillna(999.0)
    _trend["_consensus"]=pd.to_numeric(_trend.get("consensus_rank",999),errors="coerce").fillna(999.0)
    _trend["_conf"]=pd.to_numeric(_trend.get("confidence",0.5),errors="coerce").fillna(0.5)
    _trend["_opp"]=pd.to_numeric(_trend.get("opp_pg",0),errors="coerce").fillna(0.0)
    _trend["_proj"]=pd.to_numeric(_trend.get("projection",0),errors="coerce").fillna(0.0)
    _trend["_vorp"]=pd.to_numeric(_trend.get("vorp",0),errors="coerce").fillna(0.0)

    # Hard metadata checks.
    _team_clean=_trend["team"].fillna("").astype(str).str.upper().str.strip()
    _trend["_valid_team"]=~_team_clean.isin(["","NFL","FA","NONE","N/A","NAN"])
    _inj=_trend.get("injury",pd.Series("",index=_trend.index)).fillna("").astype(str).str.upper()
    _trend["_long_term_out"]=_inj.str.contains(r"IR|PUP|RESERVE|NFI",regex=True)

    # Position-specific projection floors for fantasy relevance.
    _proj_floor={"QB":12.0,"RB":3.8,"WR":3.8,"TE":3.5,"DL":5.0,"DB":5.0}
    _opp_floor={"QB":10.0,"RB":4.0,"WR":3.5,"TE":2.5,"DL":0.0,"DB":0.0}
    _trend["_proj_floor"]=_trend["position"].map(_proj_floor).fillna(5.0)
    _trend["_opp_floor"]=_trend["position"].map(_opp_floor).fillna(0.0)

    # Relevance components, normalized inside position where possible.
    _trend["_proj_pct"]=_trend.groupby("position")["_proj"].rank(pct=True).fillna(.5)
    _trend["_vorp_pct"]=_trend.groupby("position")["_vorp"].rank(pct=True).fillna(.5)

    # Lower rank/market number is better, so invert percentile.
    _trend["_market_quality"]=(1-_trend.groupby("position")["_market"].rank(pct=True)).fillna(.5)
    _trend["_rank_quality"]=(1-_trend.groupby("position")["_rank"].rank(pct=True)).fillna(.5)
    _trend["_opp_pct"]=_trend.groupby("position")["_opp"].rank(pct=True).fillna(.5)

    _trend["Fantasy Relevance"]=(
        100*(
            .34*_trend["_proj_pct"]+
            .20*_trend["_vorp_pct"]+
            .18*_trend["_market_quality"]+
            .14*_trend["_rank_quality"]+
            .10*_trend["_opp_pct"]+
            .04*_trend["_conf"].clip(0,1)
        )
    ).clip(0,100).round().astype(int)

    # Role path rules.
    _trend["_projection_ok"]=_trend["_proj"]>=_trend["_proj_floor"]
    _trend["_usage_ok"]=_trend["_opp"]>=_trend["_opp_floor"]
    _trend["_market_ok"]=_trend["_market"]<=300
    _trend["_rank_ok"]=_trend["_rank"]<=300

    # QB must look starter-relevant. Deep backups are not actionable unless their
    # projection/model relevance is already high enough to matter.
    _qb=_trend["position"].astype(str).eq("QB")
    _trend["_qb_relevant"]=(~_qb) | (
        (_trend["_proj"]>=13.0) |
        (_trend["_rank"]<=40) |
        (_trend["_market"]<=260)
    )

    # IDP needs stronger evidence than a generic projection.
    _idp=_trend["position"].astype(str).isin(["DL","DB"])
    _trend["_idp_relevant"]=(~_idp) | (
        (_trend["_proj"]>=4.8) &
        ((_trend["_rank"]<=220) | (_trend["_market"]<=300) | (_trend["_vorp"]>=0))
    )

    # Soft relevance eligibility:
    # hard-exclude only truly non-actionable cases, then let the score rank the rest.
    _trend["_minimum_signal"]=(
        (_trend["_proj"] >= (_trend["_proj_floor"]*0.72)) |
        (_trend["_usage_ok"]) |
        (_trend["_market"]<=360) |
        (_trend["_rank"]<=360) |
        (_trend["Fantasy Relevance"]>=54)
    )

    _trend["Fantasy Relevant"]=(
        _trend["_valid_team"] &
        ~_trend["_long_term_out"] &
        _trend["_minimum_signal"] &
        _trend["_qb_relevant"] &
        _trend["_idp_relevant"]
    )

    def _role_bucket(r):
        if not bool(r.get("Fantasy Relevant",False)):
            return "Not actionable"

        rel=int(r.get("Fantasy Relevance",0) or 0)
        proj=float(r.get("_proj",0) or 0)
        p=str(r.get("position",""))

        # V6.66: Role Gate must agree with relevance.
        # Strong fantasy role always requires >=80 relevance.
        if p=="QB":
            if rel>=82 and proj>=18.0:
                return "Strong fantasy role"
            if rel>=70 and proj>=14.0:
                return "Rotation / usable"
            return "Watchable role"

        if p in ("RB","WR"):
            if rel>=80 and proj>=10.0:
                return "Strong fantasy role"
            if rel>=68 and proj>=6.0:
                return "Rotation / usable"
            return "Watchable role"

        if p=="TE":
            if rel>=80 and proj>=8.0:
                return "Strong fantasy role"
            if rel>=68 and proj>=5.5:
                return "Rotation / usable"
            return "Watchable role"

        if p in ("DL","DB"):
            if rel>=80 and proj>=8.0:
                return "Strong fantasy role"
            if rel>=68 and proj>=6.5:
                return "Rotation / usable"
            return "Watchable role"

        if rel>=80:
            return "Strong fantasy role"
        if rel>=68:
            return "Rotation / usable"
        return "Watchable role"

    _trend["Role Gate"]=_trend.apply(_role_bucket,axis=1)

    # V6.67: position-normalized breakout calibration.
    # Normalize breakout strength WITHIN each position before blending relevance,
    # so DB/DL score distributions cannot crowd out RB/WR/TE.
    _trend["_raw_breakout_score"]=pd.to_numeric(
        _trend["breakout_score"],errors="coerce"
    ).fillna(0).clip(0,100)

    _trend["_pos_breakout_pct"]=_trend.groupby("position")["_raw_breakout_score"].rank(
        pct=True,method="average"
    ).fillna(0.5)

    _trend["_pos_relevance_pct"]=_trend.groupby("position")["Fantasy Relevance"].rank(
        pct=True,method="average"
    ).fillna(0.5)

    _trend["breakout_score"]=(
        60*_trend["_pos_breakout_pct"] +
        .20*_trend["_raw_breakout_score"] +
        15*_trend["_pos_relevance_pct"] +
        .05*_trend["Fantasy Relevance"]
    ).clip(0,100).round().astype(int)

    # Keep regression calibration unchanged in this version.
    _trend["regression_score"]=(
        .70*_trend["regression_score"] + .30*_trend["Fantasy Relevance"]
    ).clip(0,100).round().astype(int)

    def _action(row, kind):
        rel=int(row.get("Fantasy Relevance",0))
        owner=str(row.get("owner","FREE AGENT"))
        score=int(row.get("breakout_score" if kind=="breakout" else "regression_score",0))
        if kind=="breakout":
            if owner=="FREE AGENT":
                if rel>=78 and score>=75: return "ADD"
                if rel>=66 and score>=65: return "WATCH"
                return "IGNORE"
            return "HOLD / MONITOR"
        else:
            if owner=="FREE AGENT":
                return "IGNORE"
            if rel>=78 and score>=75: return "SELL-HIGH / BENCH"
            if rel>=65 and score>=65: return "HOLD / MONITOR"
            return "IGNORE"

    _trend["Breakout Action"]=_trend.apply(lambda r:_action(r,"breakout"),axis=1)
    _trend["Regression Action"]=_trend.apply(lambda r:_action(r,"regression"),axis=1)

    # V6.64: roster-aware waiver opportunity using BENCH replacement value.
    # An available player does not need to beat the weakest player at his own position;
    # he needs to be worth a roster spot versus the user's weakest bench asset.
    _my_name=_team_names.get("1","My Team")
    _my_rows=_trend[_trend["owner"].isin([_my_name,"My Team","Griffin"])].copy()

    # Estimate bench candidates as the lowest-value rostered players after protecting likely starters.
    _starter_need={"QB":1,"RB":2,"WR":2,"TE":1,"DL":1,"DB":1}
    _bench_parts=[]
    for _p,_g in _my_rows.groupby("position"):
        _gg=_g.copy().sort_values(
            ["Fantasy Relevance","projection","vorp"],
            ascending=[False,False,False]
        )
        _protect=int(_starter_need.get(str(_p),0))
        if len(_gg)>_protect:
            _bench_parts.append(_gg.iloc[_protect:])

    if _bench_parts:
        _bench_pool=pd.concat(_bench_parts,ignore_index=False)
    else:
        _bench_pool=_my_rows.copy()

    if not _bench_pool.empty:
        _bench_pool["_bench_value"]=(
            .50*pd.to_numeric(_bench_pool["Fantasy Relevance"],errors="coerce").fillna(0) +
            .30*pd.to_numeric(_bench_pool["projection"],errors="coerce").fillna(0)*5 +
            .20*(pd.to_numeric(_bench_pool["vorp"],errors="coerce").fillna(0)+10)
        )
        _weakest_bench_value=float(_bench_pool["_bench_value"].min())
    else:
        _weakest_bench_value=45.0

    def _roster_fit(row):
        p=str(row.get("position",""))
        proj=float(row.get("projection",0) or 0)
        rel=int(row.get("Fantasy Relevance",0))
        bo=int(row.get("breakout_score",0))
        vorp=float(row.get("vorp",0) or 0)

        candidate_value=.50*rel + .30*proj*5 + .20*(vorp+10)
        bench_edge=candidate_value-_weakest_bench_value

        # QB must clear a higher bar because a second QB has limited bench utility.
        qb_penalty=0.0
        if p=="QB":
            qb_penalty=10.0
            if rel<68 or proj<13.5:
                qb_penalty=18.0

        # Slight preference to upside bench positions in this roster format.
        upside_bonus=0.0
        if p in ("RB","WR","TE"):
            upside_bonus=4.0
        elif p in ("DL","DB"):
            upside_bonus=2.0

        score=(
            .34*rel +
            .28*bo +
            .18*max(0,min(100,(vorp+8)*6)) +
            .20*max(0,min(100,50+bench_edge*2))
            + upside_bonus
            - qb_penalty
        )
        return max(0,min(100,score))

    _trend["Waiver Opportunity"]=_trend.apply(_roster_fit,axis=1).round().astype(int)

    # Confidence / evidence layer. Prevents a single strong model score from
    # automatically becoming an ADD NOW recommendation.
    def _evidence_count(row):
        p=str(row.get("position",""))
        proj=float(row.get("projection",0) or 0)
        vorp=float(row.get("vorp",0) or 0)
        rel=int(row.get("Fantasy Relevance",0))
        rank=float(row.get("_rank",9999) or 9999)
        market=float(row.get("_market",9999) or 9999)
        opp=float(row.get("_opp",0) or 0)
        role=str(row.get("Role Gate",""))

        ev=0
        if vorp >= 1.5:
            ev += 1
        if rel >= 72:
            ev += 1
        if p in ("RB","WR","TE") and opp >= {"RB":5.0,"WR":4.5,"TE":3.5}.get(p,0):
            ev += 1
        if p in ("DL","DB") and proj >= 7.5:
            ev += 1
        if rank <= 120:
            ev += 1
        if market <= 220:
            ev += 1
        if role == "Strong fantasy role":
            ev += 1
        return ev

    _trend["Evidence"]=_trend.apply(_evidence_count,axis=1)

    def _evidence_reasons(row):
        p=str(row.get("position",""))
        proj=float(row.get("projection",0) or 0)
        vorp=float(row.get("vorp",0) or 0)
        rel=int(row.get("Fantasy Relevance",0) or 0)
        rank=float(row.get("_rank",9999) or 9999)
        market=float(row.get("_market",9999) or 9999)
        opp=float(row.get("_opp",0) or 0)
        role=str(row.get("Role Gate",""))
        reasons=[]

        if vorp>=1.5:
            reasons.append("Positive VORP")
        if rel>=72:
            reasons.append("High relevance")
        if p in ("RB","WR","TE") and opp >= {"RB":5.0,"WR":4.5,"TE":3.5}.get(p,0):
            reasons.append("Opportunity")
        if p in ("DL","DB") and proj>=7.5:
            reasons.append("Strong IDP projection")
        if rank<=120:
            reasons.append("Model rank")
        if market<=220:
            reasons.append("Market support")
        if role=="Strong fantasy role":
            reasons.append("Strong role")
        elif role=="Rotation / usable":
            reasons.append("Usable role")

        return " • ".join(reasons[:5]) if reasons else "Limited supporting evidence"

    _trend["Evidence Reasons"]=_trend.apply(_evidence_reasons,axis=1)

    # V6.69: interpretability confidence.
    # Confidence is separate from Breakout Score: a high breakout signal can still
    # be LOW confidence if role/relevance/evidence are weak.
    def _confidence_rating(row):
        rel=int(row.get("Fantasy Relevance",0) or 0)
        ev=int(row.get("Evidence",0) or 0)
        role=str(row.get("Role Gate",""))
        vorp=float(row.get("vorp",0) or 0)

        score=0
        if rel>=75: score+=2
        elif rel>=65: score+=1

        if ev>=4: score+=2
        elif ev>=2: score+=1

        if role=="Strong fantasy role": score+=2
        elif role=="Rotation / usable": score+=1

        if vorp>=1.5: score+=1
        elif vorp>=0.0: score+=0

        if score>=5:
            return "HIGH"
        if score>=3:
            return "MED"
        return "LOW"

    _trend["Confidence"]=_trend.apply(_confidence_rating,axis=1)

    def _waiver_action(row):
        if str(row.get("owner"))!="FREE AGENT":
            return "PASS"
        p=str(row.get("position",""))
        score=int(row.get("Waiver Opportunity",0))
        rel=int(row.get("Fantasy Relevance",0))
        bo=int(row.get("breakout_score",0))
        ev=int(row.get("Evidence",0))
        vorp=float(row.get("vorp",0) or 0)
        role=str(row.get("Role Gate",""))

        # QB is a special case in a one-QB league: it must be a clear upgrade,
        # not merely a good NFL starter.
        if p=="QB":
            if score>=82 and rel>=76 and ev>=3 and vorp>=1.0:
                return "WATCH"
            return "PASS"

        # ADD NOW requires both model strength and corroborating evidence.
        if score>=80 and rel>=74 and ev>=3 and vorp>=1.0:
            return "ADD NOW"

        # WATCH = legitimate fantasy-relevant player with multiple supporting signals.
        if score>=68 and rel>=64 and ev>=2 and (bo>=60 or vorp>=0.5):
            return "WATCH"

        # STASH = plausible upside/role, but evidence is not yet strong enough.
        if score>=58 and rel>=56 and ev>=1 and p in ("RB","WR","TE","DL","DB"):
            return "STASH"

        return "PASS"

    _trend["Waiver Action"]=_trend.apply(_waiver_action,axis=1)

    c0,c1,c2,c3,c4,c5=st.columns([1.05,1.15,.9,.9,.9,.9])
    with c0:
        _quick_view=st.selectbox("View",["Best Overall","Offense","IDP"],key="v668_quick_view")
    with c1:
        _scope=st.selectbox("Scope",["Available Only","My Team","Entire League"],key="v660_trend_scope")
    with c2:
        _positions=["All"]+sorted(_trend["position"].dropna().astype(str).unique().tolist())
        _pos=st.selectbox("Position",_positions,key="v660_trend_pos")
    with c3:
        _bmin=st.slider("Min breakout",50,95,65,5,key="v660_bmin")
    with c4:
        _rmin=st.slider("Min regression",50,95,65,5,key="v660_rmin")
    with c5:
        _deep=st.toggle("Include non-actionable",value=False,key="v662_deep")

    _f=_trend[_trend["projection"].notna()].copy()
    if not _deep:
        _f=_f[_f["Fantasy Relevant"]].copy()
    if _scope=="Available Only":
        # V6.74: three-way availability guard. A player is available only if
        # ownership says FA AND he is absent from taken AND absent from draft_log.
        _taken_keys={_owner_key(x) for x in (state.get("taken",[]) or []) if str(x).strip()}
        _log_keys={
            _owner_key(x.get("player",""))
            for x in (state.get("draft_log",[]) or [])
            if isinstance(x,dict) and str(x.get("player","")).strip()
        }
        _f=_f[
            (_f["owner"]=="FREE AGENT") &
            (~_f["player"].map(_owner_key).isin(_taken_keys | _log_keys))
        ]
    elif _scope=="My Team":
        _my_name=_team_names.get("1","My Team")
        _f=_f[_f["owner"].isin([_my_name,"My Team","Griffin"])]

    if _quick_view=="Offense":
        _f=_f[_f["position"].astype(str).isin(["RB","WR","TE"])]
    elif _quick_view=="IDP":
        _f=_f[_f["position"].astype(str).isin(["DL","DB"])]

    if _pos!="All":
        _f=_f[_f["position"].astype(str)==_pos]

    # V6.70: free-agent regression is not actionable, so Available Only gets
    # a full-width breakout panel. My Team / Entire League keep side-by-side views.
    if _scope=="Available Only":
        bcol=st.container()
        rcol=None
    else:
        bcol,rcol=st.columns(2)

    with bcol:
        st.markdown("### 🔥 Breakout Targets")
        st.caption("Breakout scores are normalized within position, so RBs compete with RBs, WRs with WRs, TEs with TEs, and IDPs with their own position groups. Quarterbacks remain suppressed unless they clear a much higher upside bar.")
        _hist_matches=int(_trend["last_ppg"].notna().sum()) if "last_ppg" in _trend.columns else 0
        _hist_eligible=int((pd.to_numeric(_trend["projection"],errors="coerce").fillna(0)>0).sum()) if len(_trend) else 0
        _hist_pct=round(100*_hist_matches/max(_hist_eligible,1))
        if _hist_matches:
            _src_counts=_trend.loc[_trend["last_ppg"].notna(),"history_source"].value_counts()
            _src_text=" • ".join([f"{k}: {int(v)}" for k,v in _src_counts.items()])
            st.caption(f"📚 2025 baseline: {_hist_matches} matches ({_hist_pct}% of projected pool) • {_src_text} • refreshes every 24 hr")
        else:
            st.warning("2025 FantasyPros PPG baseline could not be loaded on this run. PPG Δ will remain unavailable until the source is reachable.")
        _breakout_pool=_f[
            (_f["position"]!="QB") |
            (
                (_f["breakout_score"]>=82) &
                (_f["Fantasy Relevance"]>=76) &
                (_f["vorp"]>=1.0)
            )
        ].copy()

        _b=_breakout_pool[_breakout_pool["breakout_score"]>=_bmin].copy()
        if len(_b)<5:
            _fallback=_breakout_pool[_breakout_pool["Fantasy Relevant"]].sort_values(
                ["breakout_score","Fantasy Relevance","vorp"],
                ascending=[False,False,False]
            ).head(8)
            _b=pd.concat([_b,_fallback],ignore_index=False).drop_duplicates(subset=["player"])
        # Position normalization should allow legitimate offense to surface naturally.
        # Do not force offense into the list; keep a separate pool only for diagnostics.
        _off_pool=_breakout_pool[
            _breakout_pool["position"].isin(["RB","WR","TE"]) &
            _breakout_pool["Fantasy Relevant"]
        ].copy()
        _off_pool=_off_pool.sort_values(
            ["breakout_score","Fantasy Relevance","vorp"],
            ascending=[False,False,False]
        )

        _b=_b.sort_values(
            ["breakout_score","Fantasy Relevance","progression","vorp"],
            ascending=[False,False,False,False]
        ).head(10)
        if _b.empty:
            st.info("No players meet the current breakout threshold.")
        else:
            _bd_cols=["player","position","team","Role Gate","Fantasy Relevance","breakout_score","Confidence","projection","vorp","Breakout Action"]
            if _history_col:
                _bd_cols.insert(6,"last_ppg")
                _bd_cols.insert(7,"ppg_change")
            _bd=_b[_bd_cols].copy()
            _rename={"player":"Player","position":"Pos","team":"Team",
                     "Role Gate":"Role","Fantasy Relevance":"Rel.","breakout_score":"Breakout","Confidence":"Confidence",
                     "last_ppg":"2025 PPG","projection":"2026 PPG","vorp":"VORP","Breakout Action":"Action"}
            if _history_col:
                _rename.update({"ppg_change":"PPG Δ"})
            _bd.rename(columns=_rename,inplace=True)
            if "2025 PPG" in _bd.columns:
                _bd["2025 PPG"]=_bd["2025 PPG"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x),2))
            if "PPG Δ" in _bd.columns:
                _bd["PPG Δ"]=_bd["PPG Δ"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x),2))
            st.dataframe(_bd,use_container_width=True,hide_index=True)

            with st.expander("Why these breakout players?",expanded=False):
                st.dataframe(
                    _b[["player","why_breakout"]].rename(columns={"player":"Player","why_breakout":"Why"}),
                    use_container_width=True,hide_index=True
                )

            _off_total=len(_off_pool) if "_off_pool" in locals() else 0
            _off_above=int((_off_pool["breakout_score"]>=_bmin).sum()) if _off_total else 0
            _off_near=int(((_off_pool["breakout_score"]>=max(52,_bmin-12)) & (_off_pool["breakout_score"]<_bmin)).sum()) if _off_total else 0
            if _off_total:
                st.caption(
                    f"Position-normalized offense check: {_off_total} legitimate RB/WR/TE evaluated • "
                    f"{_off_above} above threshold • {_off_near} near-threshold."
                )

            if not _b.empty:
                _mix=_b["position"].value_counts()
                _mix_txt=" • ".join([f"{k}: {int(v)}" for k,v in _mix.items()])
                st.caption(f"Breakout mix: {_mix_txt}")

    if rcol is not None:
        with rcol:
                st.markdown("### 📉 Regression Risks")
                _r=_f[_f["regression_score"]>=_rmin].copy()
                if not _deep:
                    _r=_r[_r["owner"]!="FREE AGENT"]
                _r=_r.sort_values(
                    ["regression_score","Fantasy Relevance","regression","vorp"],ascending=[False,False,False,True]
                ).head(15)
                if _r.empty:
                    st.info("No rostered players meet the current regression threshold for this scope.")
                else:
                    _rd_cols=["player","position","team","Role Gate","Fantasy Relevance","regression_score","Confidence","projection","vorp","Regression Action"]
                    if _history_col:
                        _rd_cols.insert(6,"ppg_change")
                    _rd=_r[_rd_cols].copy()
                    _rename={"player":"Player","position":"Pos","team":"Team",
                             "Role Gate":"Role","Fantasy Relevance":"Rel.","regression_score":"Regression","Confidence":"Confidence",
                             "projection":"2026 PPG","vorp":"VORP","Regression Action":"Action"}
                    if _history_col:
                        _rename.update({"ppg_change":"PPG Δ"})
                    _rd.rename(columns=_rename,inplace=True)
                    if "PPG Δ" in _rd.columns:
                        _rd["PPG Δ"]=_rd["PPG Δ"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x),2))
                    st.dataframe(_rd,use_container_width=True,hide_index=True)
        
                    with st.expander("Why these regression risks?",expanded=False):
                        st.dataframe(
                            _r[["player","why_regression"]].rename(columns={"player":"Player","why_regression":"Why"}),
                            use_container_width=True,hide_index=True
                        )
        
    if _scope=="Available Only":
        st.info("Regression Risks is hidden in Available Only because regression of free agents is not actionable. Switch Scope to My Team or Entire League to evaluate regression risk.")

    st.markdown("### 👀 Emerging Waiver Targets")
    _watch=_f[
        (_f["owner"]=="FREE AGENT") &
        (_f["Fantasy Relevant"])
    ].copy()
    _watch=_watch.sort_values(
        ["Waiver Opportunity","Fantasy Relevance","breakout_score"],
        ascending=[False,False,False]
    )
    _actionable=_watch[_watch["Waiver Action"].isin(["ADD NOW","WATCH","STASH"])].copy()
    if len(_actionable)>=5:
        _watch=_actionable.head(10)
    else:
        _watch=_watch.head(10)
    if _watch.empty:
        st.caption("No legitimate available players are currently in the candidate pool.")
    else:
        _watch["signal"]="Trending Up"
        _watch["signal_score"]=_watch["Waiver Opportunity"]
        _wd_cols=["player","position","team","Role Gate","Fantasy Relevance","Evidence","Confidence","Waiver Action","signal_score"]
        if _history_col:
            _wd_cols += ["last_ppg","ppg_change"]
        _wd_cols += ["projection","vorp"]
        _wd=_watch[_wd_cols].copy()
        _wd.rename(columns={"player":"Player","position":"Pos","team":"Team",
                            "Role Gate":"Role","Fantasy Relevance":"Rel.","Evidence":"Ev.","Confidence":"Confidence",
                            "Waiver Action":"Action","signal_score":"Waiver","last_ppg":"2025 PPG","ppg_change":"PPG Δ",
                            "projection":"2026 PPG","vorp":"VORP"},inplace=True)
        if "2025 PPG" in _wd.columns:
            _wd["2025 PPG"]=_wd["2025 PPG"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x),2))
        if "PPG Δ" in _wd.columns:
            _wd["PPG Δ"]=_wd["PPG Δ"].apply(lambda x: "N/A" if pd.isna(x) else round(float(x),2))
        st.dataframe(_wd,use_container_width=True,hide_index=True)

        with st.expander("Why these waiver targets?",expanded=False):
            st.dataframe(
                _watch[["player","Evidence Reasons"]].rename(columns={"player":"Player","Evidence Reasons":"Why"}),
                use_container_width=True,hide_index=True
            )

    _hidden=int((~_trend["Fantasy Relevant"]).sum()) if not _deep else 0
    if not _deep:
        st.caption(f"Relevance-first gate active: {_hidden} non-actionable players are hidden.")
    st.caption("V6.81 keeps Breakout / Regression scoring frozen. The shared status layer now reads real injury-specific player fields instead of relying on the production board's blank/stale injury column.")

with tabs[6]:
    st.subheader("🏁 Weekly Start / Sit")
    st.caption("V7.30 Schedule Cache-Bust + Official Week 1 Fallback — V7.27 Compact Decision View is FROZEN. The same approved layout remains, while urgency, roster-impact, and command-center intelligence improve underneath.")

    _my=board[board["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    _v677_season=int(_v678_live_week.get("season",datetime.now().year))
    _v677_week=int(_v678_live_week.get("week",1))

    if _my.empty:
        st.info("Add your Yahoo roster under League Setup.")
    else:
        _starters,_bench,_lineup_score=_v676_optimize_lineup(_my)
        _practice_series=_my.get("practice_status",pd.Series("",index=_my.index)).fillna("").astype(str).str.strip()
        _injury_watch_rows=_my.apply(lambda r:_v682_injury_risk(r)!="🟢 LOW",axis=1)
        _watch_total=int(_injury_watch_rows.sum())
        _practice_known=int(_practice_series.ne("").sum())

        # Build the same evidence-rich starter decisions as V7.26 once, then render a compact report.
        _decision_rows=[]
        _locked_rows=[]
        _detail_rows=[]
        if len(_starters):
            for _,sr in _starters.iterrows():
                alt=_v719_best_alternative(sr,_bench)
                has_alt=alt is not None
                best_alt=float(alt.get("_start_value",0.0)) if has_alt else np.nan
                edge=float(sr["Adjusted PPG"])-best_alt if has_alt else np.nan
                src=_my[_my["player"].eq(sr["Player"])]
                src=src.iloc[0] if len(src) else pd.Series(dtype=object)
                conf_edge=edge if has_alt else 0.0
                conf=_v716_start_confidence(src,conf_edge,state.get("recommendation_history",[]),state)
                decision=_v720_decision(conf,conf_edge,src.get("injury_effective",src.get("injury","")),has_alt)
                risk=_v682_injury_risk(src)
                status=_v677_status_icon(src.get("injury_effective",src.get("injury","")))
                practice=_v680_practice_risk(src.get("practice_status",""))
                if not str(practice).strip(): practice="Pending" if risk!="🟢 LOW" else "—"
                opponent=str(src.get("_opponent","—") or "—")
                matchup=str(src.get("_matchup_grade","—") or "—")
                alt_name=str(alt.get("player","")) if has_alt else "—"
                edge_txt="—" if pd.isna(edge) else f"{edge:+.2f}"
                _urgency=_v728_decision_urgency(src,edge if has_alt else 99.0,conf,has_alt)
                row={
                    "Slot":str(sr.get("Slot","")), "Player":str(sr.get("Player","")),
                    "Decision":decision, "Urgency":_urgency, "Confidence":f"{conf}%", "Alternative":alt_name,
                    "Edge":edge_txt, "Status":status, "Practice":practice,
                    "Matchup":f"{opponent} • {matchup}" if matchup!="—" else opponent,
                    "Proj PPG":round(float(sr.get("Adjusted PPG",0)),2),
                }
                # A decision matters if it is close, has an actionable alternative, or carries injury/practice risk.
                matters=(has_alt and (pd.isna(edge) or abs(float(edge))<=1.50 or conf<70)) or risk!="🟢 LOW"
                if matters: _decision_rows.append(row)
                else: _locked_rows.append(row)

                fl,ce=_v682_weekly_band(src)
                _detail_rows.append({
                    **row,
                    "Role":_v683_role_summary(src),
                    "Return Ramp":_v722_injury_return_label(src),
                    "Ramp Basis":_v722_injury_return_basis(src),
                    "Practice Trend":str(src.get("practice_trend","") or "—"),
                    "Recent PPG":round(_v682_num(src,"_recent_ppg3",0),2),
                    "Injury":str(src.get("injury_detail","") or "—"),
                    "Floor":round(fl,2), "Ceiling":round(ce,2),
                    "External PPG":round(_v682_num(src,"_external_week_projection",0),2) if _v719_external_projection_valid(src) else "N/A",
                })

        _decision_count=len(_decision_rows)
        _bench_value=float(_bench["_start_value"].head(6).sum()) if len(_bench) else 0.0
        _major_flags=int(_my.apply(lambda r:_v721_injury_return_multiplier(r)<0.5,axis=1).sum())

        m1,m2,m3,m4=st.columns(4)
        m1.metric("Projected lineup",f"{_lineup_score:.1f} PPG")
        m2.metric("Decisions that matter",_decision_count,help="Close calls and starters with injury/practice concerns")
        m3.metric("Injury / practice watch",_watch_total,help=f"{_major_flags} major availability flag(s)")
        m4.metric("Bench depth",f"{_bench_value:.1f}",help=f"{len(_bench)} bench player(s)")

        st.markdown("### 🎯 Decisions That Matter")
        st.caption("Only close lineup calls or starters with injury/practice concerns. Everything else is collapsed below.")
        if _decision_rows:
            _dec=pd.DataFrame(_decision_rows)
            st.dataframe(_dec[["Slot","Player","Decision","Confidence","Alternative","Edge","Status","Practice","Matchup"]],use_container_width=True,hide_index=True)
        else:
            st.success("No meaningful lineup decisions need attention right now. Your optimized starters are clear.")

        if _locked_rows:
            with st.expander(f"✅ Locked / clear starters ({len(_locked_rows)})",expanded=False):
                _lk=pd.DataFrame(_locked_rows)
                st.dataframe(_lk[["Slot","Player","Status","Practice","Matchup","Proj PPG"]],use_container_width=True,hide_index=True)

        # Injury/practice report: only monitored players, compact by default.
        if _watch_total:
            with st.expander(f"🚨 Injury & Practice Report ({_watch_total})",expanded=False):
                _watch_df=_my.loc[_injury_watch_rows].copy()
                _ir=[]
                for _,r in _watch_df.iterrows():
                    _ps=str(r.get("practice_status","") or "").strip()
                    _ir.append({
                        "Player":str(r.get("player","") or ""),
                        "Status":_v677_status_icon(r.get("injury_effective",r.get("injury",""))),
                        "Practice":_v680_practice_risk(_ps) if _ps else "Pending",
                        "Trend":str(r.get("practice_trend","") or "—"),
                        "Injury":str(r.get("injury_detail","") or "—"),
                        "Return Ramp":_v722_injury_return_label(r),
                    })
                st.dataframe(pd.DataFrame(_ir),use_container_width=True,hide_index=True)
                _watch_practice=int((_practice_series.ne("") & _injury_watch_rows).sum())
                st.caption(f"Official practice coverage: {_watch_practice}/{_watch_total} monitored players • {_practice_known}/{len(_my)} roster players. Pending means participation has not been published; Fantasy Edge does not invent a practice designation.")

        with st.expander("ℹ️ Why? Decision details",expanded=False):
            if _detail_rows:
                _dd=pd.DataFrame(_detail_rows)
                if _decision_rows:
                    _names={r["Player"] for r in _decision_rows}
                    _dd=_dd[_dd["Player"].isin(_names)]
                st.dataframe(_dd[["Slot","Player","Alternative","Edge","Role","Return Ramp","Ramp Basis","Practice Trend","Recent PPG","External PPG","Floor","Ceiling"]],use_container_width=True,hide_index=True)
            else:
                st.caption("No starter details available.")

        with st.expander(f"🪑 Bench / Sit ({len(_bench)})",expanded=False):
            if len(_bench):
                _b=_bench.copy()
                _b["Projected PPG"]=pd.to_numeric(_b["projection"],errors="coerce").round(2)
                _b["Adjusted PPG"]=_b["_start_value"].round(2)
                _b["Status"]=_b["injury"].map(_v677_status_icon)
                _b["Practice"]=_b.get("practice_status",pd.Series("",index=_b.index)).map(_v680_practice_risk)
                _b["Opponent"]=_b.get("_opponent",pd.Series("—",index=_b.index))
                _b["Matchup"]=_b.get("_matchup_grade",pd.Series("—",index=_b.index))
                st.dataframe(_b[["player","position","Status","Practice","Opponent","Matchup","Adjusted PPG"]].rename(columns={"player":"Player","position":"Pos"}),use_container_width=True,hide_index=True)
            else:
                st.caption("No bench players found.")

        with st.expander("🧭 Decision urgency",expanded=False):
            if _detail_rows:
                _ud=pd.DataFrame(_detail_rows)
                _ud=_ud[_ud["Urgency"].ne("🟢 NO ACTION")]
                if len(_ud):
                    st.dataframe(_ud[["Player","Urgency","Decision","Alternative","Edge","Confidence"]],use_container_width=True,hide_index=True)
                else:
                    st.success("No lineup action is urgent right now.")
            st.caption("Urgency is a workflow layer only. It does not change projections, return ramps, or Start/Sit scoring.")

        with st.expander("⚙️ Advanced / Full Data",expanded=False):
            st.caption("Full engine output for troubleshooting and deeper analysis. This data still powers every recommendation above.")
            if _detail_rows:
                st.dataframe(pd.DataFrame(_detail_rows),use_container_width=True,hide_index=True)
            st.markdown("#### Practice coverage diagnostics")
            if _watch_total:
                _watch_df=_my.loc[_injury_watch_rows].copy()
                _diag=[]
                for _,r in _watch_df.iterrows():
                    _ps=str(r.get("practice_status","") or "").strip()
                    issue="Practice available" if _ps else str(r.get("practice_match_status","") or "no practice report matched")
                    _diag.append({
                        "Player":str(r.get("player","") or ""), "Team":str(r.get("team","") or ""),
                        "Practice":_ps or "PENDING", "Prior Practice":str(r.get("prior_practice_status","") or "—"),
                        "Source":str(r.get("practice_source","") or "—"), "Report state":issue,
                        "Updated":str(r.get("injury_updated","") or "—")
                    })
                st.dataframe(pd.DataFrame(_diag),use_container_width=True,hide_index=True)

        st.caption(f"Fantasy Edge V7.29 • {_v677_season} Week {_v677_week} • Same V7.26 engine, simpler decision-first report.")

with tabs[7]:
    name=st.selectbox("Player",all_names)
    p=board[board["player"].eq(name)].iloc[0]
    a,b,c,d=st.columns(4)
    a.metric("Projected PPG",f"{p.projection:.1f}")
    b.metric("Last PPG",f"{p.last_ppg:.1f}")
    c.metric("Profile",p.profile)
    d.metric("Confidence",f"{p.confidence:.0%}")
    st.write({"Team":p.team,"Position":p.position,"Listed position":p.raw_position,
              "Progression score":round(float(p.progression),1),"Regression score":round(float(p.regression),1),
              "Model rank":int(p.model_rank),"Consensus rank":None if pd.isna(p.consensus_rank) else int(p.consensus_rank),
              "Yahoo status":"My team" if name in state["my_team"] else "Taken" if name in state["taken"] else "Available"})


with tabs[8]:
    st.subheader("📊 Recommendation Tracker + Self-Evaluation")
    _v715_vs=_v715_validation_status(board,state,state.get("recommendation_history",[]),int(_v678_live_week.get("season",datetime.now().year)),int(_v678_live_week.get("week",1)))
    _v15a,_v15b,_v15c=st.columns(3)
    _v15a.metric("Current-season role samples",_v715_vs["current_role_players"])
    _v15b.metric("Graded weeks",_v715_vs["graded_weeks"])
    _v15c.metric("Live week",f"{_v715_vs['season']} W{_v715_vs['week']}")
    if _v715_vs["current_role_players"]==0:
        st.caption("Pregame mode: historical role is context-only. Current-season usage automatically takes over when weekly game stats publish.")
    st.caption(
        "Save Fantasy Edge's pregame recommendations, then grade them against actual weekly results. "
        "The tracker measures the model; it does not automatically rewrite weights after one week."
    )

    _v684_season=int(_v678_live_week.get("season",datetime.now().year))
    _v684_week=int(_v678_live_week.get("week",1))
    _history=state.setdefault("recommendation_history",[])

    _waiver_snapshot_df=globals().get("_best",pd.DataFrame())
    _current_snapshot=_v684_build_snapshot(
        board,state,_v684_season,_v684_week,
        _waiver_snapshot_df if isinstance(_waiver_snapshot_df,pd.DataFrame) else None
    )

    c1,c2,c3=st.columns(3)
    c1.metric("Current NFL context",f"{_v684_season} W{_v684_week}")
    c2.metric("Saved weeks",len(_history))
    _current_saved=next((s for s in _history if s.get("key")==_v684_snapshot_key(_v684_season,_v684_week)),None)
    c3.metric("This week", "Saved ✅" if _current_saved else "Not saved")

    st.markdown("### 1) Lock in this week's recommendations")
    st.caption(
        "Do this after your roster/waiver/injury data are current and before games. "
        "Saving again for the same week replaces that week's prior snapshot."
    )
    if st.button("💾 Save / refresh this week's recommendations",key="v684_save_snapshot",type="primary"):
        if not _current_snapshot:
            st.error("No roster snapshot could be created. Confirm your roster under League Setup.")
        else:
            _history=[s for s in _history if s.get("key")!=_current_snapshot["key"]]
            _history.append(_current_snapshot)
            _history=sorted(_history,key=lambda s:(int(s.get("season",0)),int(s.get("week",0))))
            state["recommendation_history"]=_history
            save_state(state)
            st.success(
                f"Saved {_current_snapshot['key']}: "
                f"{len(_current_snapshot.get('start_sit',[]))} start/sit calls, "
                f"{len(_current_snapshot.get('waivers',[]))} waiver calls and "
                f"{len(_current_snapshot.get('role_watch',[]))} role-trend watches."
            )
            st.rerun()

    if _current_snapshot:
        with st.expander("Preview what will be tracked",expanded=False):
            _preview=pd.DataFrame(_current_snapshot.get("start_sit",[]))
            if len(_preview):
                cols=[c for c in ["slot","starter","alternative","edge","confidence","decision","projection","adjusted_projection","role_trend","injury"] if c in _preview.columns]
                st.dataframe(_preview[cols],use_container_width=True,hide_index=True)
            if _current_snapshot.get("waivers"):
                st.caption(f"{len(_current_snapshot['waivers'])} Add/Drop recommendations will also be tracked.")

    st.markdown("### 2) Grade a saved week")
    if not _history:
        st.info("No recommendation snapshots have been saved yet.")
    else:
        _week_labels=[s.get("key","") for s in reversed(_history)]
        _selected=st.selectbox("Saved week",_week_labels,key="v684_grade_week")
        _snap=next((s for s in _history if s.get("key")==_selected),None)
        _grade=_v684_grade_snapshot(_snap,state)

        if not _grade or not _grade.get("ready"):
            st.info("Actual results are not available for this saved week yet. Keep the snapshot; it will grade automatically once weekly stats are published.")
            if st.session_state.get("_v684_actuals_error"):
                st.caption("Actuals feed: "+str(st.session_state.get("_v684_actuals_error")))
        else:
            a,b,c,d=st.columns(4)
            a.metric(
                "Start/Sit accuracy",
                "—" if _grade["start_sit_accuracy"] is None else f"{_grade['start_sit_accuracy']:.1f}%",
                help=f"{_grade['start_sit_correct']} correct of {_grade['start_sit_scored']} comparisons with both actual scores available."
            )
            b.metric(
                "Projection MAE",
                "—" if _grade["projection_mae"] is None else f"{_grade['projection_mae']:.2f}"
            )
            _mae_delta=None
            if _grade["projection_mae"] is not None and _grade["adjusted_mae"] is not None:
                _mae_delta=_grade["projection_mae"]-_grade["adjusted_mae"]
            c.metric(
                "Decision-layer MAE",
                "—" if _grade["adjusted_mae"] is None else f"{_grade['adjusted_mae']:.2f}",
                delta=None if _mae_delta is None else f"{_mae_delta:+.2f} vs raw"
            )
            d.metric(
                "High-confidence accuracy",
                "—" if _grade["high_conf_accuracy"] is None else f"{_grade['high_conf_accuracy']:.1f}%"
            )

            if _grade.get("decisions"):
                st.markdown("#### Start/Sit audit")
                st.dataframe(pd.DataFrame(_grade["decisions"]),use_container_width=True,hide_index=True)

            w1,w2,w3=st.columns(3)
            w1.metric(
                "Matchup adjustments helped",
                "—" if _grade["matchup_help_rate"] is None else f"{_grade['matchup_help_rate']:.0f}%"
            )
            w2.metric(
                "This-week waiver wins",
                f"{_grade['waiver_wins']}/{_grade['waiver_scored']}" if _grade["waiver_scored"] else "—",
                help="Only compares the recommended add vs drop in that week's actual scoring; ROS recommendations need more time."
            )
            w3.metric(
                "Role-trend follow-through",
                f"{_grade['role_hits']}/{_grade['role_scored']}" if _grade["role_scored"] else "—"
            )

            if _grade.get("waivers"):
                with st.expander("Waiver recommendation audit"):
                    st.dataframe(pd.DataFrame(_grade["waivers"]),use_container_width=True,hide_index=True)

            if _grade.get("role_rows"):
                with st.expander("Role-trend audit"):
                    st.dataframe(pd.DataFrame(_grade["role_rows"]),use_container_width=True,hide_index=True)

    st.markdown("### 3) Multi-week model report")
    _summary=_v684_history_summary(_history,state)
    if _summary.empty:
        st.caption("The multi-week report will populate after at least one saved week has published actual results.")
    else:
        st.dataframe(_summary,use_container_width=True,hide_index=True)

        _acc=pd.to_numeric(_summary["Start/Sit Accuracy"],errors="coerce").dropna()
        _raw=pd.to_numeric(_summary["Projection MAE"],errors="coerce").dropna()
        _adj=pd.to_numeric(_summary["Adjusted MAE"],errors="coerce").dropna()
        q1,q2,q3=st.columns(3)
        q1.metric("Avg Start/Sit accuracy","—" if _acc.empty else f"{_acc.mean():.1f}%")
        q2.metric("Avg raw projection MAE","—" if _raw.empty else f"{_raw.mean():.2f}")
        q3.metric("Avg decision-layer MAE","—" if _adj.empty else f"{_adj.mean():.2f}")

        if len(_summary)>=3 and not _raw.empty and not _adj.empty:
            if _adj.mean() < _raw.mean():
                st.success(
                    f"Across graded weeks, matchup/injury/role adjustments are improving error by "
                    f"{(_raw.mean()-_adj.mean()):.2f} points on average."
                )
            else:
                st.warning(
                    f"Across graded weeks, the decision layer is currently adding "
                    f"{(_adj.mean()-_raw.mean()):.2f} points of MAE. "
                    "That is a tuning signal—not an automatic reason to rewrite weights from one result."
                )

    st.markdown("### 4) Confidence calibration")
    _cal=_v696_confidence_bins(_history,state)
    if _cal.empty:
        st.caption("Calibration begins once enough saved Start/Sit calls have published actual results.")
    else:
        st.dataframe(_cal,use_container_width=True,hide_index=True)
        if len(_cal[_cal["Status"].eq("OVERCONFIDENT")]):
            st.warning("At least one confidence band is overconfident. Calibration only activates with 5+ graded calls in that band.")
        elif len(_cal[_cal["Status"].eq("UNDERCONFIDENT")]):
            st.info("At least one confidence band is underconfident; calibration can move upward with enough evidence.")
        else:
            st.success("Observed confidence is currently reasonably calibrated.")
    if _v695_saved and _v695_saved_key:
        st.success(f"Automatic weekly checkpoint saved: {_v695_saved_key}")
    else:
        st.caption("Automatic checkpoints: Thursday pregame, Sunday morning, and Sunday final pregame on first app open in each window.")

    with st.expander("Tracker controls"):
        st.caption("Snapshots are stored inside the same Fantasy Edge cloud/local league state.")
        if _history and st.button("Delete selected saved week",key="v684_delete_week"):
            _sel=st.session_state.get("v684_grade_week")
            if _sel:
                state["recommendation_history"]=[s for s in _history if s.get("key")!=_sel]
                save_state(state)
                st.success(f"Deleted {_sel}.")
                st.rerun()

    st.caption(
        "V6.84 creates the feedback loop: save recommendations before games, grade them afterward, "
        "and look for multi-week patterns before tuning Fantasy Edge."
    )


# ---------------- V6.86 IDP Intelligence ----------------
with tabs[9]:
    st.subheader("🧠 IDP Intelligence")
    st.caption("Dedicated DL/DB layer using projection, recent scoring, role, matchup and VORP.")
    x=board[board["position"].isin(["DL","DB"])].copy()
    if x.empty: st.info("No DL/DB players found.")
    else:
        x[["IDP Score","Tier"]]=x.apply(lambda r:pd.Series(_v686_idp_intelligence(r)),axis=1)
        x["Owner"]=x["player"].map(lambda n:"MY TEAM" if _player_owner(state,n)=="1" else "FA" if _player_owner(state,n)=="FA" else "ROSTERED")
        x["Role"]=x.apply(_v683_role_summary,axis=1); x["Status"]=x["injury"].map(_v677_normalize_injury_status)
        cols=["player","position","team","Owner","Tier","IDP Score","projection","_recent_ppg3","vorp","Role","_matchup_grade","Status"]
        st.dataframe(x.sort_values(["IDP Score","projection"],ascending=False)[cols].rename(columns={"player":"Player","position":"Pos","team":"Team","projection":"Proj","_recent_ppg3":"Recent PPG","vorp":"VORP","_matchup_grade":"Matchup"}),use_container_width=True,hide_index=True)

# ---------------- V6.87 Consensus Watch ----------------
with tabs[10]:
    st.subheader("📡 V6.92 External Projection Consensus")
    st.caption(
        "Compares Fantasy Edge against live external weekly projections. Sleeper is automatic; "
        "FantasyPros joins the consensus when an API key is configured in Streamlit secrets."
    )

    _v692_season=int(_v678_live_week.get("season",datetime.now().year))
    _v692_week=int(_v678_live_week.get("week",1))
    try:
        _v692_fp_key=str(st.secrets.get("FANTASYPROS_API_KEY","") or "")
    except Exception:
        _v692_fp_key=""

    _cons=_v692_consensus_table(board,_v692_season,_v692_week,_v692_fp_key)
    _sleeper_matches=int(_cons["Sleeper"].notna().sum()) if "Sleeper" in _cons.columns else 0
    _fp_matches=int(_cons["FantasyPros"].notna().sum()) if "FantasyPros" in _cons.columns else 0
    _any_matches=int((_cons["External Sources"]>0).sum()) if "External Sources" in _cons.columns else 0

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Sleeper matches",_sleeper_matches)
    c2.metric("FantasyPros matches",_fp_matches)
    c3.metric("Any external match",_any_matches)
    c4.metric("NFL context",f"{_v692_season} W{_v692_week}")

    if not _v692_fp_key:
        st.info(
            "Sleeper external projections are active. Add FANTASYPROS_API_KEY to Streamlit secrets "
            "if you want a second external provider in the consensus."
        )

    _cf=st.selectbox(
        "Show",
        ["Biggest disagreements","Major only","All matched players"],
        key="v692_filter"
    )
    _view=_cons[_cons["External Sources"]>0].copy()
    if _cf=="Major only":
        _view=_view[_view["Consensus Flag"].eq("⚠️ MAJOR DISAGREEMENT")]
    if not _view.empty:
        _view["_abs_diff"]=pd.to_numeric(_view["FE vs External"],errors="coerce").abs()
        _view=_view.sort_values("_abs_diff",ascending=False)
        cols=[
            "player","position","team","Fantasy Edge","Sleeper","FantasyPros",
            "External Consensus","FE vs External","External Spread",
            "External Sources","Decision Layer","Consensus Flag"
        ]
        cols=[c for c in cols if c in _view.columns]
        st.dataframe(
            _view[cols].head(150).rename(columns={
                "player":"Player","position":"Pos","team":"Team"
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No external projections matched the current player pool yet.")

    st.caption(
        "External Consensus is calculated only from external providers that returned a player match; "
        "Fantasy Edge itself is never included in that consensus number."
    )

# ---------------- V6.88 Opportunity Detector ----------------
with tabs[11]:
    st.subheader("🚨 Opportunity Detector")
    st.caption("Finds usage changes before the fantasy box score fully catches up.")
    x=board.copy(); x["Opportunity Flag"]=x.apply(_v688_opportunity_flag,axis=1); x=x[x["Opportunity Flag"].ne("")].copy()
    if x.empty: st.info("No strong opportunity signals right now.")
    else:
        x["Owner"]=x["player"].map(lambda n:"MY TEAM" if _player_owner(state,n)=="1" else "FA" if _player_owner(state,n)=="FA" else "ROSTERED")
        cols=["player","position","team","Owner","Opportunity Flag","_role_trend","_role_delta","_opps_last","_targets_last","_carries_last","_recent_ppg3","projection"]
        st.dataframe(x.sort_values(["_role_delta","_opps_last"],ascending=False)[cols].rename(columns={"player":"Player","position":"Pos","team":"Team","_role_trend":"Role","_role_delta":"Role Δ","_opps_last":"Last Opps","_targets_last":"Targets","_carries_last":"Carries","_recent_ppg3":"Recent PPG","projection":"Proj"}),use_container_width=True,hide_index=True)

# ---------------- V6.89 League Intelligence ----------------
with tabs[12]:
    st.subheader("🕵️ V6.93 League-Specific Scarcity")
    st.caption(
        "Measures positional supply using your actual 12-team ownership state, free-agent quality "
        "and replacement-level weekly value."
    )

    st.markdown("### Positional market")
    _sc=_v693_scarcity.copy().sort_values("Scarcity Score",ascending=False)
    st.dataframe(_sc,use_container_width=True,hide_index=True)

    _tight=_sc.iloc[0] if len(_sc) else None
    if _tight is not None:
        st.info(
            f"Tightest market: {_tight['Position']} — {_tight['Tier']} "
            f"({float(_tight['Scarcity Score']):.0f}/100), with "
            f"{int(_tight['Startable FAs'])} startable free agents by the current replacement threshold."
        )

    st.markdown("### All 12 rosters")
    rows=[]
    for owner in [str(i) for i in range(1,13)]:
        d=_v689_team_strength(board,state,owner)
        d["Team"]=state.get("team_names",{}).get(owner,f"Team {owner}")
        rows.append(d)
    df=pd.DataFrame(rows).sort_values("score",ascending=False)
    st.dataframe(
        df[["Team","score","strength","weakness","roster"]].rename(columns={
            "score":"Lineup Score","strength":"Strength","weakness":"Need","roster":"Rostered"
        }),
        use_container_width=True,
        hide_index=True
    )

    st.markdown("### Scarcity premium on available players")
    _fa=board[board["player"].map(lambda n:_player_owner(state,n)=="FA")].copy()
    if len(_fa):
        _fa=_fa.sort_values(["_scarcity_premium","projection"],ascending=False)
        st.dataframe(
            _fa[["player","position","team","projection","_replacement_ppg","_scarcity_score","_scarcity_premium"]]
            .head(60)
            .rename(columns={
                "player":"Player","position":"Pos","team":"Team","projection":"Proj",
                "_replacement_ppg":"Replacement PPG",
                "_scarcity_score":"Scarcity",
                "_scarcity_premium":"Scarcity Premium"
            }),
            use_container_width=True,
            hide_index=True
        )

    st.caption(
        "Scarcity premium is now included in trade asset value. It does not rewrite the core Fantasy Edge projection or VORP."
    )

# ---------------- V6.90 Trade Analyzer ----------------
with tabs[13]:
    st.subheader("🔁 V7.34 Actionable Trade Recommendations")
    st.caption(
        "Only surfaces trades worth acting on. V7.34 keeps the fast V7.33 search, but the main recommendation list now requires a meaningful recommendation tier and a non-negative partner outcome. Marginal or partner-negative ideas are moved to a collapsed secondary section."
    )

    my=board[board["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    other=board[board["player"].map(lambda n:_player_owner(state,n) not in ("1","FA"))].copy()

    if my.empty or other.empty:
        st.info("Need your roster plus opponent rosters to generate trade partners.")
    else:
        _ideas=_v694_trade_partner_suggestions(board,state,25)
        st.markdown("### Trades That Improve Your Team")

        # V7.34 presentation gate: the primary list is for actionable trades only.
        # Keep marginal / partner-negative model ideas available for transparency,
        # but do not present them beside moves that are actually worth pursuing.
        if _ideas.empty:
            _actionable=_ideas.copy()
            _secondary=_ideas.copy()
        else:
            _rec=_ideas.get("Recommendation",pd.Series("",index=_ideas.index)).astype(str)
            _partner=pd.to_numeric(_ideas.get("Partner Gain",pd.Series(0,index=_ideas.index)),errors="coerce").fillna(0)
            _meaningful=~_rec.str.contains("MARGINAL",case=False,na=False)
            _partner_ok=_partner >= 0.0
            _actionable=_ideas[_meaningful & _partner_ok].copy()
            _secondary=_ideas[~(_meaningful & _partner_ok)].copy()

        if _actionable.empty:
            st.success("HOLD — No mutually worthwhile trade currently clears the recommendation gate.")
            if not _secondary.empty:
                st.caption(f"{len(_secondary)} model-positive idea(s) were suppressed because the gain is marginal or the other manager is projected to get worse.")
        else:
            st.metric("Meaningful opportunities",int(len(_actionable)))
            _show_cols=[c for c in ["Recommendation","Trade Fit","Grade","Partner","Type","You Give","You Get","Lineup Gain","Your Gain","ROS Change","Depth Change","Partner Gain"] if c in _actionable.columns]
            st.dataframe(_actionable[_show_cols].head(10),use_container_width=True,hide_index=True)
            _best_trade=_actionable.iloc[0]
            st.markdown(
                f"**Best path — {_best_trade['Recommendation']}:** {_best_trade['You Give']} → {_best_trade['You Get']} "
                f"with {_best_trade['Partner']}  •  **{float(_best_trade['Lineup Gain']):+.2f} lineup PPG** "
                f"• ROS **{float(_best_trade['ROS Change']):+.1f}%** • depth **{float(_best_trade['Depth Change']):+.2f}** "
                f"• partner **{float(_best_trade['Partner Gain']):+.2f}** "
                f"• **{int(_best_trade['Trade Fit'])}% fit ({_best_trade['Grade']})**"
            )
            if str(_best_trade.get("Trade-off","")).strip():
                st.caption(str(_best_trade["Trade-off"]))
            with st.expander("Why these trades rank here", expanded=False):
                st.dataframe(
                    _actionable[[c for c in ["Recommendation","Partner","You Give","You Get","Your Need","Their Need","Asset Gap","ROS Change","Depth Change","Partner Gain","Realism","Trade-off","Why"] if c in _actionable.columns]].head(10),
                    use_container_width=True,hide_index=True
                )

        if not _secondary.empty:
            with st.expander(f"Other possible trades — not recommended ({len(_secondary)})", expanded=False):
                st.caption("These are kept for transparency only. They are marginal upgrades and/or make the other manager's optimized roster worse, so Fantasy Edge does not recommend pursuing them.")
                _other_cols=[c for c in ["Recommendation","Partner","Type","You Give","You Get","Lineup Gain","Your Gain","ROS Change","Depth Change","Partner Gain","Trade Fit"] if c in _secondary.columns]
                st.dataframe(_secondary[_other_cols].head(10),use_container_width=True,hide_index=True)

        st.caption(
            "V7.34 main-list gate: positive Your Gain + non-marginal recommendation + non-negative Partner Gain. Technical possibilities stay available below without cluttering the actionable list."
        )

        st.markdown("### Manual trade analyzer")
        give=st.multiselect(
            "You give",
            sorted(my["player"].tolist()),
            max_selections=3,
            key="v694_give"
        )
        get=st.multiselect(
            "You receive",
            sorted(other["player"].tolist()),
            max_selections=3,
            key="v694_get"
        )
        if give and get:
            _get_df=other[other["player"].isin(get)].copy()
            _owners=sorted({_player_owner(state,n) for n in _get_df["player"] if _player_owner(state,n) not in ("1","FA")})
            if len(_owners)!=1:
                st.error("All players you receive must come from the same opponent roster. Mixed-opponent packages are not valid trades.")
            else:
                _opp_owner=_owners[0]
                _opp_df=_v694_owner_roster(board,state,_opp_owner)
                ev=_v717_full_trade_eval(
                    my[my["player"].isin(give)].copy(),_get_df,my,_opp_df
                )
                if ev:
                    a,b,c,d=st.columns(4)
                    a.metric("Your lineup gain",f"{ev['Roster Gain']:+.2f}")
                    b.metric("Partner lineup gain",f"{ev['Partner Gain']:+.2f}")
                    c.metric("Asset value",f"{ev['Net Asset Value']:+.2f}")
                    d.metric("Verdict",ev["Verdict"])
                    st.dataframe(pd.DataFrame([ev]),use_container_width=True,hide_index=True)

        st.caption(
            "Trade value now includes a league-specific scarcity premium, but the optimizer still judges the effect on your real starting lineup and depth."
        )

# ---------------- V7.36 Early Injury News + Roster Contingency Hotfix ----------------
_NEWS_INJURY_TERMS=("injury","injured","surgery","procedure","meniscus","sprain","strain","hamstring","knee","ankle","shoulder","concussion","miss","out","week-to-week","questionable","doubtful")
_NEWS_HIGH_TERMS=("surgery","procedure","expected to miss","will miss","miss a game","miss 1","miss 2","meniscus","placed on ir","injured reserve","out indefinitely")

@st.cache_data(ttl=900,show_spinner=False)
def _v735_google_news_player(player):
    """Breaking-news layer only. It never overwrites the official NFL designation."""
    try:
        q=quote_plus(f'"{player}" (injury OR surgery OR miss OR questionable OR knee OR ankle OR hamstring OR concussion) when:2d')
        url=f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
        r=requests.get(url,timeout=5,headers={"User-Agent":"Mozilla/5.0 FantasyEdge/7.35"})
        r.raise_for_status(); root=ET.fromstring(r.content)
        rows=[]
        for item in root.findall('.//item')[:12]:
            title=(item.findtext('title') or '').strip(); desc=re.sub('<[^>]+>',' ',item.findtext('description') or '')
            text=(title+' '+desc).lower()
            if norm(player) not in norm(title+' '+desc): continue
            if not any(k in text for k in _NEWS_INJURY_TERMS): continue
            rows.append({"Player":player,"Headline":title,"Published":item.findtext('pubDate') or '',"URL":item.findtext('link') or '',"_text":text})
        return rows[:3]
    except Exception:
        return []

def _v735_is_verified_reserve(row):
    """Safe reserve-list check using the existing V6.79 authority map/status fields."""
    key=_owner_key(row.get('player',row.get('Player','')))
    fixed=_V679_VERIFIED_RESERVE.get(key,{}) if isinstance(_V679_VERIFIED_RESERVE,dict) else {}
    fixed_status=_v677_normalize_injury_status(fixed.get('status','')) if fixed else 'ACTIVE'
    effective=_v677_normalize_injury_status(row.get('injury_effective',row.get('injury','')))
    return fixed_status in ('IR','PUP','NFI','SUSPENDED') or effective in ('IR','PUP','NFI','SUSPENDED')

def _v735_has_injury_concern(row):
    """Normalize V6.82's emoji-labelled risk output into a real concern boolean."""
    risk=str(_v682_injury_risk(row) or '').upper()
    return not ('LOW' in risk and 'LOW-MOD' not in risk) and '🟢' not in risk

def _v735_news_watch(board_df,state):
    return _v742_news_watch(board_df,state)

def _v735_contingency(board_df,state,news_df):
    if news_df is None or news_df.empty: return pd.DataFrame()
    my=board_df[board_df['player'].map(lambda n:_player_owner(state,n)=='1')].copy()
    rows=[]
    for _,nw in news_df.iterrows():
        if int(nw.get('Depth',99))>1: continue
        pos=str(nw.get('Pos',''))
        if pos not in ('QB','TE','K','DL','DB'): continue
        # Reuse the exact ranked transaction already produced by Waiver Wire so the
        # Command Center can never name a different add/drop pair.
        shared=pd.DataFrame(st.session_state.get("_v742_waiver_transactions",[]))
        if len(shared):
            shared=shared[(shared.get('Pos',pd.Series('',index=shared.index)).astype(str)==pos) & shared.get('Emergency Coverage',pd.Series(False,index=shared.index)).fillna(False).astype(bool)]
        if len(shared):
            pick=shared.sort_values(['Transaction Score','Decision Score'],ascending=False).iloc[0]
            rows.append({"Player":nw['Player'],"Need":f"{pos} contingency","Best Available":str(pick.get('Add','')),"Proj PPG":round(float(pick.get('Effective Add PPG',0) or 0),2),"Action":"ADD CONTINGENCY" if nw.get('News Risk')=='HIGH' else 'WATCH / PREPARE',"Drop":str(pick.get('Drop','')),"Transaction Score":round(float(pick.get('Transaction Score',0) or 0),1)})
            continue
        fa=board_df[(board_df['position'].astype(str)==pos) & board_df['player'].map(lambda n:_is_free_agent(state,n))].copy()
        if fa.empty: continue
        fa['_v']=fa.apply(_v676_player_value,axis=1)
        add=fa.sort_values(['_v','projection'],ascending=False).iloc[0]
        # Suggest the replacement target now; existing V7.14 waiver guard remains the authority on any drop.
        rows.append({"Player":nw['Player'],"Need":f"{pos} contingency","Best Available":str(add.get('player','')),"Proj PPG":round(float(add.get('projection',0) or 0),2),"Action":"ADD CONTINGENCY" if nw.get('News Risk')=='HIGH' else 'WATCH / PREPARE',"Drop":"Use Waiver Wire protected-drop guard"})
    return pd.DataFrame(rows)

# ---------------- V6.91 Weekly Command Center ----------------
with tabs[14]:
    st.subheader("🏠 Weekly Command Center")
    st.caption("One-page summary of your most important weekly Fantasy Edge decisions.")
    my=board[board["player"].map(lambda n:_player_owner(state,n)=="1")].copy()
    if my.empty: st.info("Set your roster under League Setup to populate the Command Center.")
    else:
        _early_news=_v735_news_watch(board,state)
        _contingency=_v735_contingency(board,state,_early_news)
        if isinstance(_early_news,pd.DataFrame) and not _early_news.empty:
            st.error(f"🚨 Early Injury Warning — {len(_early_news)} roster player(s) have breaking availability news before/alongside the official designation.")
            _ncols=[c for c in ["Player","Pos","News Risk","Official Status","Expected","Headline"] if c in _early_news.columns]
            st.dataframe(_early_news[_ncols],use_container_width=True,hide_index=True)
            st.caption("News Watch is an early-warning layer only. It does not falsely mark a player OUT; official NFL/practice status remains authoritative and automatically takes over when published.")
            if isinstance(_contingency,pd.DataFrame) and not _contingency.empty:
                st.markdown("### 🛟 Roster contingency")
                st.dataframe(_contingency,use_container_width=True,hide_index=True)
                st.caption("Because you have no active depth at that position, Fantasy Edge prepares a replacement immediately. Any actual drop still must clear the frozen V7.14 protected-drop guard in Waiver Wire.")
        starters,bench,lineup=_v676_optimize_lineup(my); top=_v691_top_waiver(board,state); weakness=_v691_roster_weakness(board,state)
        injured=my[my["injury"].map(_v677_normalize_injury_status).ne("ACTIVE")]; rising=my[my["_role_trend"].astype(str).str.contains("RISING",na=False)]
        a,b,c,d=st.columns(4); a.metric("Optimized lineup",f"{lineup:.1f}"); b.metric("Roster weakness",weakness); c.metric("Injury flags",len(injured)); d.metric("Role risers",len(rising))
        st.markdown("### Start these")
        st.dataframe(starters[["Slot","Player","Pos","Opponent","Matchup","Adjusted PPG","Status","Practice"]],use_container_width=True,hide_index=True)
        if len(bench):
            bdf=bench.copy(); bdf["Value"]=bdf.apply(_v676_player_value,axis=1)
            st.markdown("### Best bench alternatives")
            st.dataframe(bdf.sort_values("Value",ascending=False)[["player","position","team","Value","_role_trend","injury"]].head(8).rename(columns={"player":"Player","position":"Pos","team":"Team","_role_trend":"Role","injury":"Status"}),use_container_width=True,hide_index=True)
        st.markdown("### 🆕 What changed since the latest saved checkpoint")
        _changes=_v715_weekly_changes(board,state,state.get("recommendation_history",[]),int(_v678_live_week.get("season",datetime.now().year)),int(_v678_live_week.get("week",1)),10)
        if _changes.empty:
            st.caption("No material projection, injury, role, or external-consensus changes detected on your roster since the latest saved checkpoint.")
        else:
            st.dataframe(_changes,use_container_width=True,hide_index=True)

        st.markdown("### Market intelligence")
        _tight=_v693_scarcity.sort_values("Scarcity Score",ascending=False).iloc[0] if len(_v693_scarcity) else None
        _trade_ideas=_v694_trade_partner_suggestions(board,state,5)
        try:
            _cc_fp_key=str(st.secrets.get("FANTASYPROS_API_KEY","") or "")
        except Exception:
            _cc_fp_key=""
        _cc_cons=_v692_consensus_table(
            my,
            int(_v678_live_week.get("season",datetime.now().year)),
            int(_v678_live_week.get("week",1)),
            _cc_fp_key
        )
        _major=int((_cc_cons.get("Consensus Flag",pd.Series(dtype=str))=="⚠️ MAJOR DISAGREEMENT").sum()) if len(_cc_cons) else 0

        m1,m2,m3=st.columns(3)
        m1.metric(
            "Tightest position",
            "—" if _tight is None else str(_tight["Position"]),
            help="Based on your league's rostered supply and startable free agents."
        )
        m2.metric("My projection disagreements",_major)
        m3.metric("Realistic trade ideas",len(_trade_ideas))

        if len(_trade_ideas):
            _ti=_trade_ideas.iloc[0]
            st.caption(
                f"Top trade path: give {_ti['You Give']} to {_ti['Partner']} for {_ti['You Get']} "
                f"• your modeled gain {_ti['Your Gain']:+.2f}"
            )

        st.markdown("### V7.28 Weekly Command Center")
        try:
            _aq_cons=_v692_consensus_table(board,int(_v678_live_week.get("season",datetime.now().year)),int(_v678_live_week.get("week",1)),_cc_fp_key)
        except Exception:
            _aq_cons=pd.DataFrame()
        try:
            _aq_trades=_v694_trade_partner_suggestions(board,state,10)
        except Exception:
            _aq_trades=pd.DataFrame()
        _queue=_v728_command_center(board,state,globals().get("_best",pd.DataFrame()),_aq_trades,5)
        if _queue.empty: st.success("No urgent roster actions detected.")
        else:
            st.dataframe(_queue,use_container_width=True,hide_index=True)
            st.caption("V7.27 Start/Sit presentation is frozen. The command center now prioritizes ACT NOW / MONITOR / REVIEW items and only surfaces waiver or trade moves that clear the existing protection guards.")
        st.markdown("### Model health")
        h1,h2,h3=st.columns(3); h1.metric("Injury coverage",f"{_v683_health.get('injury_coverage',0)}%"); h2.metric("Matchup coverage",f"{_v683_health.get('matchup_coverage',0)}%"); h3.metric("Role coverage",f"{_v683_health.get('role_coverage',0)}%")

if hist.empty and "hist_error" in st.session_state:
    st.warning("Historical nflverse data did not load, so conservative position baselines are temporarily being used.")

if isinstance(market,pd.DataFrame) and market.empty and "market_error" in st.session_state:
    st.warning("Current consensus rankings did not load, so the app is temporarily using the statistical model without the consensus reality-check layer.")


# V6.50: anchor production board/config to app.py directory so Streamlit Cloud cannot load stale repo-root CSVs.
