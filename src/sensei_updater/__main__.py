# sensei_updater/__main__.py
import sys
import traceback

def main():
    try:
        import importlib
        main_module = importlib.import_module("sensei_updater.main")
        if not hasattr(main_module, "run"):
            print("sensei_updater.main does not define run()")
            sys.exit(1)
        sys.exit(main_module.run())
    except Exception as e:
        print("Fatal startup error:", e)
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()