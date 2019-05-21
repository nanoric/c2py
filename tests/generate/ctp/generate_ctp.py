import sys

from autocxxpy.main import main

if __name__ == "__main__":
    args =(
      "vnctp ThostFtdcMdApi.h ThostFtdcTraderApi.h -I vnctp/include --output-dir vnctp/generated_files"
      " --pyi-output-dir . --no-clear-pyi-output"
      " --no-callback-pattern"
      " .*Api::.*"
      " --ignore-pattern"
      " .*THOST_FTDC_(VTC|FTC)_.*"
    )
    # sys.argv = args.split(' ')
    main(args=args.split(' '))
