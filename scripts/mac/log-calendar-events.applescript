#!/usr/bin/osascript
-- Log Calendar Events to Daily Note
-- This AppleScript fetches today's calendar events from iCloud and logs them to a daily note

-- Configuration
property workspacePath : (system attribute "HOME") & "/codex"
property dailyNotesPath : workspacePath & "/daily-notes"

-- Get today's date in YYYY-MM-DD format
set currentDate to do shell script "date '+%Y-%m-%d'"
set noteFile to dailyNotesPath & "/" & currentDate & ".md"

-- Get today's date range for calendar query
set todayStart to current date
set time of todayStart to 0 -- midnight
set todayEnd to todayStart + (24 * hours) - 1

-- Fetch calendar events
set eventsList to {}
tell application "Calendar"
	set allCalendars to every calendar
	repeat with aCalendar in allCalendars
		try
			set calendarEvents to (every event of aCalendar whose start date ≥ todayStart and start date < todayEnd)
			repeat with anEvent in calendarEvents
				set eventTitle to summary of anEvent
				set eventStart to start date of anEvent
				set eventEnd to end date of anEvent
				set eventLocation to location of anEvent
				
				-- Format time
				set startTime to do shell script "date -j -f '%A, %B %e, %Y at %I:%M:%S %p' " & quoted form of ((eventStart as string)) & " '+%H:%M' 2>/dev/null || echo '00:00'"
				set endTime to do shell script "date -j -f '%A, %B %e, %Y at %I:%M:%S %p' " & quoted form of ((eventEnd as string)) & " '+%H:%M' 2>/dev/null || echo '00:00'"
				
				-- Check if it's an all-day event
				set isAllDay to allday event of anEvent
				
				-- Build event info
				set eventInfo to {eventTitle:eventTitle, startTime:startTime, endTime:endTime, eventLocation:eventLocation, isAllDay:isAllDay, startDate:eventStart}
				set end of eventsList to eventInfo
			end repeat
		end try
	end repeat
end tell

-- Sort events by start time
set sortedEvents to my sortEventsByTime(eventsList)

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
		"## Calendar Events" & linefeed & linefeed
	
	do shell script "echo " & quoted form of noteContent & " > " & quoted form of noteFile
end if

-- Read current note content
set noteContent to do shell script "cat " & quoted form of noteFile

-- Build calendar section content
if (count of sortedEvents) = 0 then
	set calendarSection to linefeed & "No events scheduled for today." & linefeed
else
	set calendarSection to linefeed
	repeat with eventInfo in sortedEvents
		set eventTitle to eventTitle of eventInfo
		set startTime to startTime of eventInfo
		set endTime to endTime of eventInfo
		set eventLocation to eventLocation of eventInfo
		set isAllDay to isAllDay of eventInfo
		
		if isAllDay then
			set calendarSection to calendarSection & "- **All Day**: " & eventTitle
		else
			set calendarSection to calendarSection & "- **" & startTime & " - " & endTime & "**: " & eventTitle
		end if
		
		if eventLocation is not "" and eventLocation is not missing value then
			set calendarSection to calendarSection & " @ " & eventLocation
		end if
		
		set calendarSection to calendarSection & linefeed
	end repeat
	set calendarSection to calendarSection & linefeed
end if

-- Insert or update calendar section
if noteContent contains "## Calendar Events" then
	-- Replace existing calendar section
	set AppleScript's text item delimiters to "## Calendar Events"
	set noteParts to text items of noteContent
	set beforeSection to item 1 of noteParts
	set afterSection to item 2 of noteParts
	
	-- Find the next section marker to preserve content after calendar section
	set AppleScript's text item delimiters to linefeed & "## "
	set afterParts to text items of afterSection
	
	if (count of afterParts) > 1 then
		-- There's another section after calendar
		set nextSection to linefeed & "## " & item 2 of afterParts
		set noteContent to beforeSection & "## Calendar Events" & calendarSection & nextSection
		
		-- Reconstruct remaining sections
		if (count of afterParts) > 2 then
			repeat with i from 3 to count of afterParts
				set noteContent to noteContent & linefeed & "## " & item i of afterParts
			end repeat
		end if
	else
		-- Calendar section is last
		set noteContent to beforeSection & "## Calendar Events" & calendarSection
	end if
	set AppleScript's text item delimiters to ""
else
	-- Add calendar section at the beginning (after frontmatter and title)
	if noteContent contains "# Daily Note" then
		set AppleScript's text item delimiters to linefeed & linefeed
		set noteParts to text items of noteContent
		-- Find where to insert (after title)
		set headerPart to item 1 of noteParts & linefeed & linefeed & item 2 of noteParts
		set restPart to ""
		if (count of noteParts) > 2 then
			repeat with i from 3 to count of noteParts
				set restPart to restPart & linefeed & linefeed & item i of noteParts
			end repeat
		end if
		set noteContent to headerPart & linefeed & linefeed & "## Calendar Events" & calendarSection & restPart
		set AppleScript's text item delimiters to ""
	else
		-- Add at end
		set noteContent to noteContent & linefeed & "## Calendar Events" & calendarSection
	end if
end if

-- Write updated content back to file
do shell script "cat > " & quoted form of noteFile & " <<'EOF'" & linefeed & noteContent & linefeed & "EOF"

-- Show notification
set eventCount to count of sortedEvents
if eventCount = 0 then
	display notification "No events scheduled for today" with title "Calendar Events Logged"
else if eventCount = 1 then
	display notification "1 event logged" with title "Calendar Events Logged"
else
	display notification (eventCount as string) & " events logged" with title "Calendar Events Logged"
end if

return "Logged " & (count of sortedEvents) & " calendar events to " & noteFile

-- Helper function to sort events by start time
on sortEventsByTime(eventsList)
	set sortedList to {}
	repeat with i from 1 to count of eventsList
		set currentEvent to item i of eventsList
		set inserted to false
		repeat with j from 1 to count of sortedList
			set compareEvent to item j of sortedList
			if (startDate of currentEvent) < (startDate of compareEvent) then
				set sortedList to (items 1 thru (j - 1) of sortedList) & {currentEvent} & (items j thru -1 of sortedList)
				set inserted to true
				exit repeat
			end if
		end repeat
		if not inserted then
			set end of sortedList to currentEvent
		end if
	end repeat
	return sortedList
end sortEventsByTime
