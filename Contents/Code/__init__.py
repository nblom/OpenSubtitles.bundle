#opensubtitles.org
#Subtitles service allowed by www.OpenSubtitles.org

OS_API = 'http://plexapp.api.opensubtitles.org/xml-rpc'
OS_LANGUAGE_CODES = 'http://www.opensubtitles.org/addons/export_languages.php'
OS_PLEX_USERAGENT = 'plexapp.com v9.0'
#OS_PLEX_USERAGENT = 'OS Test User Agent'
subtitleExt       = ['utf','utf8','utf-8','sub','srt','smi','rt','ssa','aqt','jss','ass','idx']
 
OS_ORDER_PENALTY = -1   # Penalty applied to subs score due to position in sub list return by OS.org
OS_BAD_SUBTITLE_PENALTY = -1000 # Penalty applied to subs score due to flag bad subtitle in response.
OS_WRONG_MOVIE_KIND_PENALTY = -1000 # Penalty applied if the video have the wrong kind (episode or movie)
OS_HEARING_IMPAIRED_BONUS = 10 # Bonus added for subs hearing impaired tagged when the pref is set to yes
OS_SUBRATING_GOOD_BONUS = 20 # Bonnus added for subs with a rating of 0.0 or 10.0
OS_SUBRATING_BAD_PENALTY = -100 # Penalty for subs with a rating between 1 and 4
OS_TVSHOWS_GOOD_SEASON_BONUS = 30 # Bonus applied to TVShows subs if the season match
OS_MOVIE_IMDB_MATCH_BONUS = 50 # Bonus applied for a movie if the imdb id return by OS match the metadata in Plex

#Useless since imdb ids seems to not be in metadata available for tv shows.
OS_TVSHOWS_SHOW_IMDB_ID_MATCH_BONUS = 30 # Bonus applied to TVShows subs if the imdbID of the show match
OS_TVSHOWS_EPISODE_IMDB_ID_MATCH_BONUS = 50 # Bonus applied to TVShows subs if the imdbID of the episode match

def Start():
  HTTP.CacheTime = CACHE_1DAY
  HTTP.Headers['User-Agent'] = 'plexapp.com v9.0'

@expose
def GetImdbIdFromHash(openSubtitlesHash, lang):
  proxy = XMLRPC.Proxy(OS_API)
  try:
    os_movieInfo = proxy.CheckMovieHash('',[openSubtitlesHash])
  except:
    return None
    
  if os_movieInfo['data'][openSubtitlesHash] != []:
    return MetadataSearchResult(
      id    = "tt" + str(os_movieInfo['data'][openSubtitlesHash]['MovieImdbID']),
      name  = str(os_movieInfo['data'][openSubtitlesHash]['MovieName']),
      year  = int(os_movieInfo['data'][openSubtitlesHash]['MovieYear']),
      lang  = lang,
      score = 90)
  else:
    return None

def opensubtitlesProxy():
  proxy = XMLRPC.Proxy(OS_API)
  username = Prefs["username"]
  password = Prefs["password"]
  if username == None or password == None:
    username = ''
    password = ''
  token = proxy.LogIn(username, password, 'en', OS_PLEX_USERAGENT)['token']
  return (proxy, token)

def getLangList():
  langList = [Prefs["langPref1"]]
  if Prefs["langPref2"] != 'None' and Prefs["langPref1"] != Prefs["langPref2"]:
    langList.append(Prefs["langPref2"])
  return langList

def logFilteredSubtitleResponseItem(item):
  #Log('Keys available: %s' % subtitleResponse[0].keys())
  #Keys available: ['ISO639', 'SubComments', 'UserID', 'SubFileName', 'SubAddDate', 'SubBad', 'SubLanguageID', 'SeriesEpisode', 'MovieImdbRating', 'SubHash', 'MovieReleaseName', 'SubtitlesLink', 'IDMovie', 'SeriesIMDBParent', 'SubDownloadsCnt', 'QueryParameters', 'MovieByteSize', 'MovieKind', 'SeriesSeason', 'IDSubMovieFile', 'SubSize', 'IDSubtitle', 'IDSubtitleFile', 'MovieFPS', 'SubSumCD', 'QueryNumber', 'SubAuthorComment', 'MovieNameEng', 'MatchedBy', 'SubHD', 'SubRating', 'SubDownloadLink', 'SubHearingImpaired', 'ZipDownloadLink', 'SubFeatured', 'MovieTimeMS', 'SubActualCD', 'UserNickName', 'SubFormat', 'MovieHash', 'LanguageName', 'UserRank', 'MovieName', 'IDMovieImdb', 'MovieYear']
  Log(' - PlexScore: %d | MovieName: %s | MovieKind: %s | MovieYear: %s | MovieNameEng: %s | SubAddDate: %s | SubBad: %s | SubHearingImpaired: %s | SubRating: %s | SubDownloadsCnt: %s | IDMovie: %s | IDMovieImdb: %s' % (item['PlexScore'], item['MovieName'], item['MovieKind'], item['MovieYear'], item['MovieNameEng'], item['SubAddDate'], item['SubBad'], item['SubHearingImpaired'], item['SubRating'], item['SubDownloadsCnt'], item['IDMovie'], item['IDMovieImdb']))

def logFilteredSubtitleResponse(subtitleResponse):
  #Prety way to display subtitleResponse in Logs sorted by PlexScore
  Log('Current subtitleResponse has %d elements:' % len(subtitleResponse))
  for item in sorted(subtitleResponse, key=lambda k: k['PlexScore'], reverse=True):
    logFilteredSubtitleResponseItem(item)
    
def fetchSubtitles(proxy, token, part, language):
  # Download OS result based on hash and size
  Log('Looking for match for GUID %s and size %d and language %s' % (part.openSubtitleHash, part.size, language))
  #subtitleResponse = proxy.SearchSubtitles(token,[{'sublanguageid':language, 'moviehash':part.openSubtitleHash, 'moviebytesize':str(part.size)}])['data']
  proxyResponse = proxy.SearchSubtitles(token,[{'sublanguageid':language, 'moviehash':part.openSubtitleHash, 'moviebytesize':str(part.size)}])
  
  #Check Server Response status
  if proxyResponse['status'] != "200 OK":
    Log('Error return by XMLRPC proxy: %s' % proxyResponse['status'])
    filteredSubtitleResponse = False
  else:
    subtitleResponse = proxyResponse['data']
    #Start to process the results if the list is not empty
    if subtitleResponse != False:
      #Start to score each subs
      firstScore = 50
      filteredSubtitleResponse = []
      for sub in subtitleResponse:
        #Add default score
        sub['PlexScore'] = firstScore;

        #Add filters common to Movies and TVShows
        
        #Check if Bad Subs flag is set to 1
        if int(sub['SubBad']) == 1:
          sub['PlexScore'] = sub['PlexScore'] + OS_BAD_SUBTITLE_PENALTY

        #filter depending on the subs rating
        if sub['SubRating']=='0.0' or sub['SubRating']=='10.0':
          sub['PlexScore'] = sub['PlexScore'] + OS_SUBRATING_GOOD_BONUS
        elif float(sub['SubRating'])>0.1 and float(sub['SubRating'])<4.1:
          sub['PlexScore'] = sub['PlexScore'] + OS_SUBRATING_BAD_PENALTY

        #filter depending on a pref on SubHearingImpaired
        #TODO: Perhaps we can filter that just before download
        if Prefs['HearingImpairedPref'] == 'Yes' and int(sub['SubHearingImpaired'])==1:
          sub['PlexScore'] = sub['PlexScore'] + OS_HEARING_IMPAIRED_BONUS

        filteredSubtitleResponse.append(sub)
        #TODO: is this a good idea. With this there is no equality possible.
        firstScore = firstScore + OS_ORDER_PENALTY

      Log('hash/size search result: ')
      #logFilteredSubtitleResponse(subtitleResponse)
    else:
      filteredSubtitleResponse = False

  return filteredSubtitleResponse
    
 
def filterSubtitleResponseForMovie(subtitleResponse, proxy, token, metadata):
  imdbID = metadata.id
  #TODO: this part should be done before to apply common filter on the result by imdbID
  #if subtitleResponse == False and imdbID != '': #let's try the imdbID, if we have one...
    #Log('Found nothing via hash, trying search with imdbid: ' + imdbID)
    #subtitleResponse = proxy.SearchSubtitles(token,[{'sublanguageid':l, 'imdbid':imdbID}])['data']
    #Log(subtitleResponse)

  if subtitleResponse == False:
    filteredSubtitleResponse = False
  else:
    #I can't filter on the name of the movie due to some metadata agent return Movie name in an other language.
    
    filteredSubtitleResponse = []
    for sub in subtitleResponse:
      if sub['MovieKind']!='movie':
        sub['PlexScore']=sub['PlexScore'] + OS_WRONG_MOVIE_KIND_PENALTY

      #check if the imdbID match
      if sub['IDMovieImdb'] == metadata.id:
        sub['PlexScore'] = sub['PlexScore'] + OS_MOVIE_IMDB_MATCH_BONUS

      filteredSubtitleResponse.append(sub)
    logFilteredSubtitleResponse(filteredSubtitleResponse)
  

  return filteredSubtitleResponse
  
def filterSubtitleResponseForTVShow(subtitleResponse, season, metadata, media):
  # I can't filter on the tvshow name as some metadata agent return TVShow name in other language.
  # I can't filter on the episode dut to some difference beteween air order and DVD order.
  if subtitleResponse == False:
    filteredSubtitleResponse = False
  else:
    filteredSubtitleResponse = []
    for sub in subtitleResponse:
      #If season match add a bonus to the score
      if int(sub['SeriesSeason']) == int(season):
        sub['PlexScore'] = sub['PlexScore'] + OS_TVSHOWS_GOOD_SEASON_BONUS

      #TODO: If imdbID match add a bonus to the score
      #IDMovieImdb for episode
      #SeriesIMDBParent for TVShow
      #Impossible since IMDB id is not in metadata. Potential solution query theTVDB do find the IMDB from TVDB id

      #Check if video type match a tvshow
      if sub['MovieKind'] != 'episode':
        sub['PlexScore']=sub['PlexScore'] + OS_WRONG_MOVIE_KIND_PENALTY


      filteredSubtitleResponse.append(sub)

    logFilteredSubtitleResponse(filteredSubtitleResponse)
  return filteredSubtitleResponse

def downloadBestSubtitle(subtitleResponse, part, language):
  #Suppress all subtitle format no supported
  if subtitleResponse != False:
      for st in subtitleResponse: #remove any subtitle formats we don't recognize
        if st['SubFormat'] not in subtitleExt:
          Log('Removing a subtitle of type: ' + st['SubFormat'])
          subtitleResponse.remove(st)
  if subtitleResponse != False:
  #Download the sub with the higest PlexScore in the filtered list.
  #TODO: Perhaps choose in case of equality with Download count.
  #TODO: Perhaps HearingImpaired choice have to be done here
  #TODO: Perhaps it is possible to chose more than one sub.
    st = sorted(subtitleResponse, key=lambda k: ['PlexScore'], reverse=True)[0] #most downloaded subtitle file for current language
    Log('Best subtitle is:')
    logFilteredSubtitleResponseItem(st)
    subUrl = st['SubDownloadLink']
    subGz = HTTP.Request(subUrl, headers={'Accept-Encoding':'gzip'}).content
    subData = Archive.GzipDecompress(subGz)
    # Supression of previous sub should be there to avoid wiping a sub not anymore in OS
    part.subtitles[Locale.Language.Match(st['SubLanguageID'])][subUrl] = Proxy.Media(subData, ext=st['SubFormat'])
  else:
    Log('No subtitles available for language ' + language)


class OpenSubtitlesAgentMovies(Agent.Movies):
  name = 'OpenSubtitles.org'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.imdb']
  
  def search(self, results, media, lang):
    Log(media.primary_metadata.id)
    Log(media.primary_metadata.id.split('tt')[1].split('?')[0])
    results.Append(MetadataSearchResult(
      id    = media.primary_metadata.id.split('tt')[1].split('?')[0],
      score = 100
    ))
    
  def update(self, metadata, media, lang):
    (proxy, token) = opensubtitlesProxy()
    for i in media.items:
      Log("Movie: %s, id:%s" % (media.title, media.id))
      for part in i.parts:
        # Remove all previous subs (taken from sender1 fork)
        for l in part.subtitles:
          part.subtitles[l].validate_keys([])

        # go fetch subtilte fo each language
        for language in getLangList():
          subtitleResponse = fetchSubtitles(proxy, token, part, language)
          subtitleResponse = filterSubtitleResponseForMovie(subtitleResponse, proxy, token, metadata)
          downloadBestSubtitle(subtitleResponse, part, language)
          

class OpenSubtitlesAgentTV(Agent.TV_Shows):
  name = 'OpenSubtitles.org'
  languages = [Locale.Language.NoLanguage]
  primary_provider = False
  contributes_to = ['com.plexapp.agents.thetvdb']

  def search(self, results, media, lang):
    results.Append(MetadataSearchResult(
      id    = 'null',
      score = 100
    ))

  def update(self, metadata, media, lang):
    (proxy, token) = opensubtitlesProxy()
    for season in media.seasons:
      # just like in the Local Media Agent, if we have a date-based season skip for now.
      if int(season) < 1900:
        for episode in media.seasons[season].episodes:
          for i in media.seasons[season].episodes[episode].items:
            Log("Show: %s, Season: %s, Ep: %s, id:%s" % (media.title, season, episode, media.seasons[season].episodes[episode].id))
            for part in i.parts:
              # Remove all previous subs (taken from sender1 fork)
              for l in part.subtitles:
                part.subtitles[l].validate_keys([])

              # go fetch subtilte fo each language
              for language in getLangList():
                subtitleResponse = fetchSubtitles(proxy, token, part, language)
                subtitleResponse = filterSubtitleResponseForTVShow(subtitleResponse, season, metadata, media)
                downloadBestSubtitle(subtitleResponse, part, language)
                  
