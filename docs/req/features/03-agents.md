# Agents

- dedicated persona/instructions for each agent (see Obsidian Qwen2.5:7b series)

**roles**

- architect / planner
- coder
- reviewer
- DJane
- VJane
- redacteur / podcast sprecherin

## Coder

**Semantik**

- arbeit an sehr vielen kleinen dateien
- komplexe operationen (sed, grep, ...)
- undo-fähigkeit, wenn man ./.git auf read-only setzt
- finales HITL möglich

**Lösung**

- Grobgranular `rw` auf den projekt folder
- read-only auf `.git`



**topics**

## Deejane

**Semantik**

- fachlich komplexe logik, nicht infrastrukturell
- wenige, fachliche schnittstellen (z.b. read-only auf music db)
- schreiben nur sehr speziell

**Lösung**

- Leserechte grob-granular
- Schreiben **gar nicht** am MCP vorbei. Beispiel
  - Monique: playlist geht wunderbar
  - File Organizer: wenige operationen (cp, rm, mv) - nicht reversible -> MCP zwingend

## MCP Server


### Internet Search

### Play Music Playlist

#### Music DB aufbauen

- ID3 Tags: MusicBrainz
- BPM, Tonart, Loudness → lokal aus dem Audio analysieren, z. B. mit Essentia oder librosa. Das ist reproduzierbar und benötigt keine externe DB.
- Genre/Styles/Moods → externe Metadaten sind sinnvoller, weil das semantische Kategorien sind. MusicBrainz hat zwar Genres/Tags, aber Abdeckung und Konsistenz schwanken.
  - MusicBrainz Tags selbst: Community-Tags wie rock, alternative rock, synth-pop.
  - Discogs: sehr gute Genre- und insbesondere feinere Style-Klassifikation.


### Play SM Video Playlist

### Find E-Mails

### Send E-Mail ⚡

## Permissions

Examples

- All MCP Interfaces (separately)
- File System
- Mails (read, send separate)

Granting

- On request (e.g. file access, mail wend)
- Timed (e.g. internet, mail read)
- Permanent (e.g. music library for DJane)


## Dialogs

### Agent Monitor

### Agent Requests (Review)

### Chat Window: Agent Permssions

## Agents (Consideration)

### DJane

instructed/specialiced for assembling music playlists (m3u?).
input:
    - Spiele etwas ruhiges. 
    - Spiele Trance von Tiesto

### Anchor Woman

instructed for my special interests.
scheduled.
collect information of my interest.
create a 10 minutes audio news-flash for me.

### VJane

instructed to provide video playlists based on current interest.

input:
    - ...

### Mail Organizer

inspect new mails. assign tags/catgegories (e.g. created 2024, shopping, social, family...).
(move in mail system? bluemail? thunderbird?)