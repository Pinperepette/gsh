import subprocess
import platform
import argparse
import os
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from cryptography.fernet import Fernet
import openai
import shutil

class GshAssistant:
    def __init__(self):
        self.console = Console()
        self.system = self.detect_system()
        self.encryption_key = self.load_encryption_key()
        self.api_key = self.load_api_key()

    def detect_system(self):
        system_name = platform.system()
        if system_name == "Darwin":
            return "macOS"
        elif system_name == "Linux":
            return "Linux"
        elif system_name == "Windows":
            return "Windows"
        else:
            return "unknown"

    def load_encryption_key(self):
        key_path = Path.home() / ".config" / "gsh" / "encryption_key.key"
        if key_path.exists():
            with open(key_path, 'rb') as key_file:
                encryption_key = key_file.read()
        else:
            encryption_key = Fernet.generate_key()
            key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(key_path, 'wb') as key_file:
                key_file.write(encryption_key)
        return encryption_key

    def load_api_key(self):
        config_path = Path.home() / ".config" / "gsh"
        config_file = config_path / "api_key.txt"
        encrypted_file = config_path / "api_key_encrypted.txt"

        api_key = os.getenv('OPENAI_API_KEY')

        if api_key:
            return api_key

        if encrypted_file.exists():
            with open(encrypted_file, 'rb') as file:
                encrypted_key = file.read()
                return self.decrypt_key(encrypted_key, self.encryption_key)

        if config_file.exists():
            with open(config_file, 'r') as file:
                return file.read().strip()

        api_key = self.console.input("[bold yellow]Enter your OpenAI API key: [/bold yellow]").strip()
        with open(config_file, 'w') as file:
            file.write(api_key)
        encrypted_key = self.encrypt_key(api_key, self.encryption_key)
        with open(encrypted_file, 'wb') as file:
            file.write(encrypted_key)

        return api_key

    def encrypt_key(self, key, encryption_key):
        fernet = Fernet(encryption_key)
        encrypted_key = fernet.encrypt(key.encode())
        return encrypted_key

    def decrypt_key(self, encrypted_key, encryption_key):
        fernet = Fernet(encryption_key)
        decrypted_key = fernet.decrypt(encrypted_key).decode()
        return decrypted_key

    def get_chatgpt_response(self, prompt, request_type="command"):
        openai.api_key = self.api_key

        if request_type == "code":
            prompt = (f"Consider that the system we are on is {self.system}. The user has requested the following code snippet: '{prompt}'. "
                    f"Please provide only the exact code block without any additional text.")
        else:
            prompt = (f"Consider that the system we are on is {self.system}. The user has requested the following shell command: '{prompt}'. "
                    f"Please provide only the exact shell command without any explanation, comments, or extra text.")

        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message['content'].strip()
        if not self.is_valid_shell_command(content.split()[0]) and request_type=="command":
            self.console.print(Panel(f"[yellow bold]Explanation:[/yellow bold]\n{content}"))
            return None

        # self.console.print(Panel(f"[green bold]gsh Suggestion:[/green bold]\n{content}"))
        return content

    def is_valid_shell_command(self, command):
        """
        Determine if the command is a valid shell command by checking its availability in the system PATH.
        """
        return shutil.which(command) is not None

    def clean_command(self, command):
        lines = command.split('\n')
        clean_lines = [line for line in lines if not (line.startswith("```") or line.strip() == "")]
        return "\n".join(clean_lines).strip()

    def run_command(self, command):
        clean_command = self.clean_command(command)
        try:
            result = subprocess.run(
                f"{clean_command} 2>/dev/null",
                shell=True,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.CalledProcessError as e:
            return e.stdout, e.stderr, e.returncode

    def process_command(self, user_input, request_type="command"):
        chatgpt_response = self.get_chatgpt_response(user_input, request_type)

        if chatgpt_response:
            if request_type == "code":
                # Display code suggestion inside a panel with syntax highlighting
                self.console.print(Panel(Syntax(chatgpt_response, "python", theme="monokai", line_numbers=True), title="gsh Code Suggestion"))
            else:
                # Display the command with syntax highlighting, no panel
                self.console.print(Syntax(chatgpt_response, "bash", theme="monokai", line_numbers=False))

            # Ask for confirmation only if it's a command
            if request_type == "command":
                confirm = self.console.input("Do you want to execute the suggested command? (yes/no or y/n): ")
                if confirm.lower() in ['yes', 'y']:
                    stdout, stderr, returncode = self.run_command(chatgpt_response)
                    if stdout.strip():
                        self.console.print(Text(stdout, style="green"))
                    if stderr.strip():
                        self.console.print(Text("Errors:", style="bold red"))
                        self.console.print(Text(stderr, style="red"))
                    if returncode != 0:
                        self.console.print(Text(f"Return code: {returncode}", style="bold yellow"))
                else:
                    self.console.print("[cyan]Command not executed.[/cyan]")

def main():
    parser = argparse.ArgumentParser(description='gsh (GPT Shell) to execute commands or suggest code via ChatGPT.')
    parser.add_argument('command', nargs='+', help='Command or code to pass to ChatGPT')
    parser.add_argument('--code', action='store_true', help='Indicate that the input is a code snippet request')
    args = parser.parse_args()

    user_command = ' '.join(args.command)

    assistant = GshAssistant()
    if args.code:
        assistant.process_command(user_command, request_type="code")
    else:
        assistant.process_command(user_command, request_type="command")

if __name__ == "__main__":
    main()
