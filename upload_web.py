import os
import subprocess
from datetime import datetime

local_repo_path = r'G:\yehpage2'
commit_message = f'Automated update on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'

def git_update_and_push(repo_path, message):
    try:
        os.chdir(repo_path)
        subprocess.run(['git', 'pull'], check=True)
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', message], check=True)
        subprocess.run(['git', 'push'], check=True)

        print("Update and push completed successfully.")
    
    except subprocess.CalledProcessError as e:
        print(f"An error occurred: {e}")

git_update_and_push(local_repo_path, commit_message)
