#!/usr/bin/env bash
#
# Install Multi-Agent Interactive CLI
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_PATH="$SCRIPT_DIR/bin/multi"

echo "Multi-Agent Interactive CLI - Installation"
echo "==========================================="
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: python3 not found"
    exit 1
fi
echo "✓ Python: $(python3 --version)"

# Make executable
chmod +x "$CLI_PATH"
echo "✓ Made CLI executable"

# Installation options
echo ""
echo "Choose installation method:"
echo ""
echo "  1) Add to PATH in shell config (recommended)"
echo "  2) Create symlink in ~/bin"
echo "  3) Copy to /usr/local/bin (requires sudo)"
echo "  4) Skip - use full path"
echo ""
read -p "Select option [1-4]: " choice

case $choice in
    1)
        SHELL_CONFIG=""
        if [[ -f "$HOME/.bashrc" ]]; then
            SHELL_CONFIG="$HOME/.bashrc"
        elif [[ -f "$HOME/.zshrc" ]]; then
            SHELL_CONFIG="$HOME/.zshrc"
        else
            SHELL_CONFIG="$HOME/.bashrc"
            touch "$SHELL_CONFIG"
        fi
        
        echo "" >> "$SHELL_CONFIG"
        echo "" >> "$SHELL_CONFIG"
        echo "# Multi-Agent Interactive CLI" >> "$SHELL_CONFIG"
        echo "export PATH=\"\$PATH:$SCRIPT_DIR/bin\"" >> "$SHELL_CONFIG"
        
        echo "✓ Added to $SHELL_CONFIG"
        echo ""
        echo "Run 'source $SHELL_CONFIG' to activate, then run:"
        echo "  multi"
        ;;
        
    2)
        mkdir -p "$HOME/bin"
        ln -sf "$CLI_PATH" "$HOME/bin/multi"
        echo "✓ Symlink created: $HOME/bin/multi"
        
        if [[ ":$PATH:" == *":$HOME/bin:"* ]]; then
            echo "✓ ~/bin is in PATH"
            echo ""
            echo "Run: multi"
        else
            echo "WARNING: ~/bin not in PATH"
            echo "Add: export PATH=\"\$PATH:\$HOME/bin\""
        fi
        ;;
        
    3)
        if [[ $EUID -ne 0 ]]; then
            sudo cp "$CLI_PATH" /usr/local/bin/multi
            sudo chmod +x /usr/local/bin/multi
        else
            cp "$CLI_PATH" /usr/local/bin/multi
            chmod +x /usr/local/bin/multi
        fi
        echo "✓ Installed to /usr/local/bin/multi"
        echo ""
        echo "Run: multi"
        ;;
        
    4)
        echo "Use full path: $CLI_PATH"
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

echo ""
echo "Installation complete!"
echo ""
echo "Quick start:"
echo "  multi          # Start interactive CLI"
echo "  /help          # Show commands"
echo "  /agents        # List agents"
echo "  /agent gemini  # Switch to Gemini"
echo "  /quit          # Exit"
echo ""
