#!/usr/bin/env bash
#
# Multi-Agent Orchestrator CLI - Installation Script
# Adds the multi-cli command to your PATH
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_NAME="multi-cli"
CLI_PATH="$SCRIPT_DIR/$CLI_NAME"

echo "Multi-Agent Orchestrator CLI - Installation"
echo "============================================"
echo ""

# Check if Python is available
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found. Please install Python 3.12+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Python found: $PYTHON_VERSION"

# Check if multi-cli exists
if [[ ! -f "$CLI_PATH" ]]; then
    echo "ERROR: $CLI_PATH not found"
    exit 1
fi

# Make executable
chmod +x "$CLI_PATH"
echo "✓ Made multi-cli executable"

# Installation options
echo ""
echo "Choose installation method:"
echo ""
echo "  1) Add alias to shell config (recommended)"
echo "  2) Create symlink in ~/bin"
echo "  3) Copy to /usr/local/bin (requires sudo)"
echo "  4) Skip - use full path"
echo ""
read -p "Select option [1-4]: " choice

case $choice in
    1)
        # Add alias to shell config
        SHELL_CONFIG=""
        if [[ -f "$HOME/.bashrc" ]]; then
            SHELL_CONFIG="$HOME/.bashrc"
        elif [[ -f "$HOME/.zshrc" ]]; then
            SHELL_CONFIG="$HOME/.zshrc"
        elif [[ -f "$HOME/.bash_profile" ]]; then
            SHELL_CONFIG="$HOME/.bash_profile"
        else
            echo "No shell config found. Creating ~/.bashrc"
            SHELL_CONFIG="$HOME/.bashrc"
            touch "$SHELL_CONFIG"
        fi
        
        echo ""
        echo "Adding alias to $SHELL_CONFIG"
        
        # Check if alias already exists
        if grep -q "alias multi=" "$SHELL_CONFIG" 2>/dev/null; then
            echo "WARNING: 'multi' alias already exists in $SHELL_CONFIG"
            read -p "Overwrite? [y/N]: " overwrite
            if [[ "$overwrite" != "y" && "$overwrite" != "Y" ]]; then
                echo "Aborted."
                exit 1
            fi
            # Remove old alias
            sed -i '/alias multi=/d' "$SHELL_CONFIG"
        fi
        
        echo "" >> "$SHELL_CONFIG"
        echo "# Multi-Agent Orchestrator CLI" >> "$SHELL_CONFIG"
        echo "alias multi='$CLI_PATH'" >> "$SHELL_CONFIG"
        echo "alias orchestrator='$CLI_PATH'" >> "$SHELL_CONFIG"
        
        echo "✓ Alias added to $SHELL_CONFIG"
        echo ""
        echo "Run 'source $SHELL_CONFIG' or restart your terminal to use:"
        echo "  multi run \"Build a REST API\""
        echo "  multi list"
        echo "  multi --help"
        ;;
        
    2)
        # Create symlink in ~/bin
        mkdir -p "$HOME/bin"
        ln -sf "$CLI_PATH" "$HOME/bin/multi"
        
        echo "✓ Symlink created: $HOME/bin/multi -> $CLI_PATH"
        echo ""
        
        # Check if ~/bin is in PATH
        if [[ ":$PATH:" == *":$HOME/bin:"* ]]; then
            echo "✓ ~/bin is in your PATH"
            echo ""
            echo "You can now use:"
            echo "  multi run \"Build a REST API\""
            echo "  multi --help"
        else
            echo "WARNING: ~/bin is not in your PATH"
            echo "Add this to your $SHELL_CONFIG:"
            echo '  export PATH="$HOME/bin:$PATH"'
        fi
        ;;
        
    3)
        # Copy to /usr/local/bin
        if [[ $EUID -ne 0 ]]; then
            echo "This option requires sudo privileges."
            sudo cp "$CLI_PATH" /usr/local/bin/multi
            sudo chmod +x /usr/local/bin/multi
            echo "✓ Installed to /usr/local/bin/multi"
        else
            cp "$CLI_PATH" /usr/local/bin/multi
            chmod +x /usr/local/bin/multi
            echo "✓ Installed to /usr/local/bin/multi"
        fi
        
        echo ""
        echo "You can now use:"
        echo "  multi run \"Build a REST API\""
        echo "  multi --help"
        ;;
        
    4)
        echo "Skipping installation."
        echo ""
        echo "Use the full path to run:"
        echo "  $CLI_PATH run \"Build a REST API\""
        echo "  $CLI_PATH --help"
        ;;
        
    *)
        echo "Invalid option."
        exit 1
        ;;
esac

echo ""
echo "Installation complete!"
echo ""
echo "Quick start:"
echo "  multi info          # Show project info"
echo "  multi agents        # Check agent availability"
echo "  multi run \"...\"     # Run a task"
echo "  multi list          # List sessions"
echo "  multi --help        # Show all commands"
echo ""
