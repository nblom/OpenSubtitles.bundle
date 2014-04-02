# OpenSubtitles.org metadata agent for Plex improvment prototype

------
## Why this fork ?

This fork is a prototype for an improvement of the Plex metadata agent used by default to fetch subtitles on OpenSubtitles.org.

The origin version used a simple algorithm:
> - Search subs by using hash and size of the video file
> - Get the sub with the most downloads.
> - If no results try with the IMDB id instead of the hash/size (only for movies)
 
This algorithm isn't efficient enough since the OpenSubtitles.org database is fed by many sources which are not rigorous enough and can mixup some data.

**Results in Plex: it's difficult to have the good subs for our movie using it.**

So this fork is a mock-up to try to have better result by making some consistency check on the results returned by OpenSubtitles.org.

-------

## How to help ?

  - Download the zip package from this last release: [on the Github Release page][1]
  - Replace the old metadata agent (OpenSubtitles.bundle) in Plugin folder by the new one in the zip archive. Don't forget to rename it with the name "OpenSubtitles.bundle" (remove the tag reference in the bundle name).
  - Try to used it to check if results are improved.
  - Share your comments and results on the Plex Forums [on this thread][2]
  - Give your ideas on the algorithm
  - Open issues on Github with usefull information (like video name, hash, size, sub language and logs)

-----
## Description of the algorithm
The main idea is to compare metadata associated to the subtitle file in the Opensubtitles.org database and the metadata associated to the video file in your local Plex database. Depending of the data and the result of the comparaison a bonus or a penalty is applied to the score of the subtitle.

### Common to movies and TV shows
> - Search Opensubtiltes.org database by using video file hash ans size
> - Default score for each subs is set to 50
> - Currently order in the opensubtitles.org response is not taken into account due to preconisation on their forums.
> - If subs have the flag SubBad then reduce the score with OS_BAD_SUBTITLE_PENALTY penalty (currently 1000)
> - If subs rating is 0.0 or 10.0 then add a bonus OS_SUBRATING_GOOD_BONUS to the score (currently 20)
> - If subs rating is between 0.1 and 4.1 then reduce the score  with OS_SUBRATING_BAD_PENALTY penalty (currently 100)



### Only for movies
>  - If sub movieKind attribute is not set to "movie" then reduce the score with OS_WRONG_MOVIE_KIND_PENALTY penalty (currently 1000)
>  - If IMDB id associated to the sub match the IMDB id associated to the video file add a bonus OS_MOVIE_IMDB_MATCH_BONUS to the score. (currently 50)
>  - If movie name match (only if you use english language for your primary agent) then add a bonus OS_TITLE_MATCH_BONUS to the score (currently 10)

### Only for TV shows
>  - If sub movieKind attribute is not set to "episode" then reduce the score with OS_WRONG_MOVIE_KIND_PENALTY penalty (currently 1000)
>  - If episode IMDB id associated to the sub match the episode IMDB id associated to the video file (only if you use TheTVDB as primary agent) then add a bonus OS_TVSHOWS_EPISODE_IMDB_ID_MATCH_BONUS to the score. (currently 50)
>  - If show IMDB id associated to the sub match the show IMDB id associated to the video file (only if you use TheTVDB as primary agent) then add a bonus OS_TVSHOWS_SHOW_IMDB_ID_MATCH_BONUS  to the score. (currently 30)
>  - If season associated to the sub match the season of the video file then add a bonus OS_TVSHOWS_GOOD_SEASON_BONUS to the score (currently 30)
>  - If show and episode name match (only if you use english language for your primary agent) then add a bonus OS_TITLE_MATCH_BONUS to the score (currently 10)
>  - If episode number match then add a bonus OS_TVSHOWS_GOOD_EPISODE_BONUS to the score (currently 10)

### Selection of the best subtitle

>  - Remove in the list the subs with an unsupported format
>  - Remove in the list the subs with a score below an acceptable threshold OS_ACCEPTABLE_SCORE_TRIGGER (currently 0)
>  - The sub with the highest score is selected to be downloded. If there is more than one sub with the same score then the sub with the highest download count is selected.



--------
## FAQ

### Where are the logs ?
See Plex help subject: [Channel Log Files][3]
The log file of this metadata agent is in the file **com.plexapp.agents.opensubtitles**

### How to find the hash and size of my video ?
Search in the log file **com.plexapp.agents.opensubtitles** the line:
> Looking for match for GUID XXXX and size YYYY and language ZZZ


### Is there any auto update ?
No, there is no auto update for this metadata agent. If I release a new version you have to overwrite the previous version. 

### How to stop test and revert to official OpenSubtitles metadata agent ?
Simple. Suppress the OpenSubtitles.bundle folder in the Plugin folder and quit and relauch Plex Media Server.

> Written with [StackEdit](https://stackedit.io/).


  [1]: https://github.com/oncleben31/OpenSubtitles.bundle/releases
  [2]: https://forums.plex.tv/index.php/topic/102923-mock-up-for-opensubtitles-metadata-agent-improvement/
  [3]: https://plexapp.zendesk.com/hc/en-us/articles/201106148-Channel-Log-Files