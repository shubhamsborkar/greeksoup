---
title: The update failed
nav: Update failed
description: What to do when a GreekSoup update stops, an antivirus flags a file, the strip says a file could not be written, or the new version misbehaves: what an update never touches, the retry, the rollback, and the report the strip links.
lead: An update replaces the desk's own files and never yours. When it stops partway, nothing of yours has changed, the strip says which files were skipped and why, and one more click finishes it. When the new version misbehaves, one line goes back.
---

## What an update touches, and what it never touches

It copies the desk's program files and pages, and adds any file under `data/` that you lack. It never writes your settings file, the day's token, your lists, your research vault, `cache/`, `logs/` or a file you or your agent changed. Since the 19 September 2026 versions the update carries no installers and no website files, so nothing in it downloads or runs anything; it reads every file it is about to write before it writes any, and a hold on one file stops the copy before it begins. [Getting a newer version](/docs/install/updates/).

## "An antivirus spoke up"

A reader's Bitdefender flagged the install script and asked to restart. The script no longer travels inside updates, and the desk removes it from its own folder at start, so there is nothing left for the alarm to fire on. Let it restart if it asks, open the desk, click **Update the desk** once more. No exclusion to add. [If your antivirus speaks up](/docs/install/windows/#if-your-antivirus-speaks-up).

## "One file could not be written"

The strip names it. Something on the computer holds that file open (an antivirus scan, an editor, a sync client). The version is not stamped, so the desk asks for one more click; close what holds the file and click again. The report the strip links carries the count of files already copied, which is the answer to the first question anyone will ask.

## The new version misbehaves

The desk keeps the files each update replaced, three versions back. Tell your agent "go back to the previous version of the desk", or in the desk folder type:

```
python updater.py rollback
```

then start the desk. Your files stay as they are either way. Then tell us what misbehaved, through Tell us in the sidebar or [an issue](https://github.com/shubhamsborkar/greeksoup/issues/new/choose), so the next version does not.

## On Windows, when the desk stops coming back

The always-on service applies a pending update by itself after the desk exits three times within a minute, so a half-applied update heals on the next start. If the address stays blank, [The page is blank](/docs/install/the-page-is-blank/) has the four things to try.

## A copy from before the strip

A desk installed before updates had a strip has no button. Paste the install line for your system again; it brings the desk up to date and keeps your files. [Install](/docs/install/).
