import sys

from autocxxpy.main import main

if __name__ == "__main__":
    args =(
      "vnitap iTapTradeAPI.h -I vnitap/include -o vnitap/generated_files"
      " --output-arg-pattern .*API::.*(sessionID$|.*ClientBuyOrderNo$|.*ClientSellOrderNo$)"
      " --no-callback-pattern .*API::.*"
    )
    # sys.argv = args.split(' ')
    main(args=args.split(' '))
