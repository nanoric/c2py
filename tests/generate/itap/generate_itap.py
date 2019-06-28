import sys

from autocxxpy.cli import generate

if __name__ == "__main__":
    args =(
      "vnitap"
      " iTapTradeAPI.h TapQuoteAPI.h TapAPIError.h iTapAPIError.h"
      " -I vnitap/include"
      " -A custom/custom_wrappers.hpp"
      " --output-dir vnitap/generated_files"
      " --pyi-output-dir ."
      " --no-clear-pyi-output"
      " --output-arg-pattern"
      " (.*API::.*(sessionID$|.*ClientBuyOrderNo$|.*ClientSellOrderNo$|.*ClientOrderNo$))|(.*Result)"
      " --no-callback-pattern"
      " .*API::.*"
    )
    # sys.argv = args.split(' ')
    generate(args=args.split(' '))
