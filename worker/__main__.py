"""
Worker module entry point - allows running worker.run_job_task as a module.
This enables: python -m worker.run_job_task
"""

from .run_job_task import main

if __name__ == "__main__":
    main()
