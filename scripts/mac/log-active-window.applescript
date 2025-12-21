#!/usr/bin/osascript
-- Log Active Window to Daily Note
-- This AppleScript logs the currently active application and window to a daily note

-- Configuration
property workspacePath : (system attribute "HOME") & "/codex"
property dailyNotesPath : workspacePath & "/daily-notes"

-- Get today's date in YYYY-MM-DD format
set currentDate to do shell script "date '+%Y-%m-%d'"
set currentTime to do shell script "date '+%H:%M:%S'"
set noteFile to dailyNotesPath & "/" & currentDate & ".md"

-- Get active application and window information
tell application "System Events"
	set frontApp to name of first application process whose frontmost is true
	set appName to frontApp
	
	tell process frontApp
		try
			set windowTitle to name of front window
		on error
			set windowTitle to "(No window)"
		end try
	end tell
end tell

-- Try to get URL if it's a browser
set browserURL to ""
set isBrowser to false

-- Check Safari
if appName is "Safari" then
	set isBrowser to true
	try
		tell application "Safari"
			set browserURL to URL of front document
		end tell
	end try
end if

-- Check Chrome
if appName contains "Chrome" or appName contains "Google Chrome" then
	set isBrowser to true
	try
		tell application appName
			set browserURL to URL of active tab of front window
		end tell
	end try
end if

-- Check Brave
if appName contains "Brave" then
	set isBrowser to true
	try
		tell application "Brave Browser"
			set browserURL to URL of active tab of front window
		end tell
	end try
end if

-- Check Microsoft Edge
if appName contains "Edge" or appName contains "Microsoft Edge" then
	set isBrowser to true
	try
		tell application "Microsoft Edge"
			set browserURL to URL of active tab of front window
		end tell
	end try
end if

-- Check Arc
if appName is "Arc" then
	set isBrowser to true
	try
		tell application "Arc"
			set browserURL to URL of active tab of front window
		end tell
	end try
end if

-- Create daily notes directory if it doesn't exist
do shell script "mkdir -p " & quoted form of dailyNotesPath

-- Check if daily note exists, if not create it
set noteExists to false
try
	do shell script "test -f " & quoted form of noteFile
	set noteExists to true
end try

if not noteExists then
	-- Create new daily note with frontmatter
	set noteContent to "---" & linefeed & ¬
		"title: Daily Note - " & currentDate & linefeed & ¬
		"date: " & currentDate & linefeed & ¬
		"tags:" & linefeed & ¬
		"  - daily-note" & linefeed & ¬
		"  - auto-generated" & linefeed & ¬
		"---" & linefeed & linefeed & ¬
		"# Daily Note - " & currentDate & linefeed & linefeed & ¬
		"## Active Windows" & linefeed & linefeed
	
	do shell script "echo " & quoted form of noteContent & " > " & quoted form of noteFile
end if

-- Read current note content
set noteContent to do shell script "cat " & quoted form of noteFile

-- Create window entry
set windowEntry to linefeed & "::: window" & linefeed & ¬
	"**Time**: " & currentTime & linefeed & ¬
	"**App**: " & appName & linefeed & ¬
	"**Window**: " & windowTitle

if isBrowser and browserURL is not "" then
	set windowEntry to windowEntry & linefeed & "**URL**: " & browserURL
end if

set windowEntry to windowEntry & linefeed & ":::" & linefeed

-- Append window entry to note
if noteContent contains "## Active Windows" then
	-- Add after Active Windows header
	set AppleScript's text item delimiters to "## Active Windows"
	set noteParts to text items of noteContent
	set noteContent to (item 1 of noteParts) & "## Active Windows" & (item 2 of noteParts) & windowEntry
	set AppleScript's text item delimiters to ""
else
	-- Add Active Windows section
	if noteContent contains "## Commits" then
		-- Add before Commits section
		set AppleScript's text item delimiters to "## Commits"
		set noteParts to text items of noteContent
		set noteContent to (item 1 of noteParts) & linefeed & "## Active Windows" & linefeed & windowEntry & linefeed & "## Commits" & (item 2 of noteParts)
		set AppleScript's text item delimiters to ""
	else
		-- Add at end
		set noteContent to noteContent & linefeed & "## Active Windows" & linefeed & windowEntry
	end if
end if

-- Write updated content back to file
do shell script "cat > " & quoted form of noteFile & " <<'EOF'" & linefeed & noteContent & linefeed & "EOF"

-- Show notification
display notification "Logged: " & appName & " - " & windowTitle with title "Active Window Logged"

return "Logged window to " & noteFile
