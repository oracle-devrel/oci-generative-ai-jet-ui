Output assets/tui-chat.gif
Set Shell bash
Set FontSize 14
Set Width 1200
Set Height 700
Set Theme "Catppuccin Mocha"
Set Padding 10

Type "cd /home/ubuntu/git/personal/agent-reasoning/tui && ./agent-tui"
Enter
Sleep 4s

# Navigate sidebar
Sleep 1s
Type "j"
Sleep 300ms
Type "j"
Sleep 300ms
Type "j"
Sleep 300ms
Type "k"
Sleep 300ms

# Select CoT agent
Type "k"
Sleep 200ms
Enter
Sleep 500ms

# Type a query
Type "What is the meaning of life in one sentence?"
Sleep 500ms
Enter

# Watch streaming response
Sleep 8s

# Show final result
Sleep 2s
