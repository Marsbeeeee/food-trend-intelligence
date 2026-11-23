"""Command entry point for the four-stage workflow."""
import sys
if __name__ == '__main__':
    if len(sys.argv)>1 and sys.argv[1]=='review-report':
        from pipeline.review_report import main
        main(sys.argv[2:])
    else:
        from workflow import main
        main()
