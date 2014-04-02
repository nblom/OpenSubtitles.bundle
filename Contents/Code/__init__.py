#opensubtitles.org
#Subtitles service allowed by www.OpenSubtitles.org
import re

OS_API = 'http://plexapp.api.opensubtitles.org/xml-rpc'
OS_LANGUAGE_CODES = 'http://www.opensubtitles.org/addons/export_languages.php'
OS_PLEX_USERAGENT = 'plexapp.com v9.0'
subtitleExt       = ['utf','utf8','utf-8','sub','srt','smi','rt','ssa','aqt','jss','ass','idx']
 
OS_ORDER_PENALTY = 0   # Penalty applied to subs score due to position in sub list return by OS.org. this value is set to 0 (previously -1) due to the OS default order is inconsistent (see forum discusion)
OS_BAD_SUBTITLE_PENALTY = -1000 # Penalty applied to subs score due to flag bad subtitle in response.
OS_WRONG_MOVIE_KIND_PENALTY = -1000 # Penalty applied if the video have the wrong kind (episode or movie)
OS_HEARING_IMPAIRED_BONUS = 10 # Bonus added for subs hearing impaired tagged when the pref is set to yes
OS_SUBRATING_GOOD_BONUS = 20 # Bonus added for subs with a rating of 0.0 or 10.0
OS_SUBRATING_BAD_PENALTY = -100 # Penalty for subs with a rating between 1 and 4
OS_TVSHOWS_GOOD_SEASON_BONUS = 30 # Bonus applied to TVShows subs if the season match
OS_TVSHOWS_GOOD_EPISODE_BONUS =  10 # Bonus applied if TH shows epiode number match
OS_MOVIE_IMDB_MATCH_BONUS = 50 # Bonus applied for a movie if the imdb id return by OS match the metadata in Plex
OS_TVSHOWS_SHOW_IMDB_ID_MATCH_BONUS = 30 # Bonus applied to TVShows subs if the imdbID of the show match
OS_TVSHOWS_EPISODE_IMDB_ID_MATCH_BONUS = 50 # Bonus applied to TVShows subs if the imdbID of the episode match
OS_ACCEPTABLE_SCORE_TRIGGER = 0 #Subs with score below this trigger will be removed
OS_TITLE_MATCH_BONUS = 10 # Bonus applied to video file if title in OS and in Plex match

TVDB_SITE  = 'http://thetvdb.com'
TVDB_PROXY = 'http://thetvdb.plexapp.com'
TVDB_API_KEY    = 'D4DDDAEFAD083E6F'
#TODO: Check with a Plex developper if the new URL without API key is OK ?
#TVDB_SERIES_URL = '%s/api/%s/series/%%s' % (TVDB_PROXY,TVDB_API_KEY) I use the adress below due to some HTML redirection badly interpreted by the current code in XML.ElementFromString()
TVDB_SERIES_URL = '%s/data/series/%%s' % (TVDB_PROXY)

HEADERS = {'User-agent': 'Plex/Nine'}

#Class to identify different search mode
class OS_Search_Methode:
    Hash, IMDB, Name = range(0, 3)

# Function taken from TheTVDB metadata agent
#TODO: Perhaps it is possible to use the function directly with the @expose decorator.
def GetResultFromNetwork(url, fetchContent=True):

    Log("Retrieving URL: " + url)

    try:
      result = HTTP.Request(url, headers=HEADERS, timeout=60)
    except:
      try:
        url = url.replace(TVDB_PROXY, TVDB_SITE)
        Log("Falling back to non-proxied URL: " + url)
        result = HTTP.Request(url, headers=HEADERS, timeout=60)
      except:
        return None

    if fetchContent:
      result = result.content

    return result

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
  try:
    proxyResponse = proxy.LogIn(username, password, 'en', OS_PLEX_USERAGENT)
    if proxyResponse['status'] != "200 OK":
      Log('Error return by XMLRPC proxy: %s' % proxyResponse['status'])
      token = False
    else:
      token = proxyResponse['token']
  except Exception, e:
    Log('Unexpected error with OpenSubtitles.org XMLRPC API : %s' % str(e))
    token = False

 
  return (proxy, token)

def getLanguageOfPrimaryAgent(guid):
  #extract from the guid the language used by the primary_agent
  primaryAgentLanguage = None
  m = re.match(r'.*\?lang=(?P<primaryAgentLanguage>\w+)$', guid)
  if m != None:
    if m.group('primaryAgentLanguage') != False:
      primaryAgentLanguage = m.group('primaryAgentLanguage')
  return primaryAgentLanguage

def getImdBShowIdfromTheTVDB(guid):
  #Extract from guid the primary data agent and the id of the show
  showIMDBId = False 
  m = re.match(r"(?P<primary_agent>.+):\/\/(?P<showID>\d+)", guid)
  if m != None:
    #Log("primary_agent: %s | showID: %s | seasonID: %s | episodeID: %s" % (m.group('primary_agent'), m.group('showID'), m.group('seasonID'), m.group('episodeID')))
    #If primary agent is TheTVDB, extract the tvshow and episode IMDN ids
    if m.group('primary_agent') ==  "com.plexapp.agents.thetvdb":
      #Fetch the IMDB show ID
      xml = XML.ElementFromString(GetResultFromNetwork(TVDB_SERIES_URL % m.group('showID')))
      showIMDBId = xml.xpath('//Data/Series/IMDB_ID')[0].text
      if showIMDBId != None:
        showIMDBId = showIMDBId.replace('tt', '')
      
  return  showIMDBId


def getImdBEpisodeIdfromTheTVDB(guid):
  #Extract from guid the primary data agent and the id of the epiosde
  #Log("GUID episode: %s" % guid)
  episodeIMDBId = False 
  m = re.match(r"(?P<primary_agent>.+):\/\/(?P<showID>\d+)\/(?P<seasonID>\d+)\/(?P<episodeID>\d+)", guid)
  if m != None:
    #Log("primary_agent: %s | showID: %s | seasonID: %s | episodeID: %s" % (m.group('primary_agent'), m.group('showID'), m.group('seasonID'), m.group('episodeID')))
    #If primary agent is TheTVDB, extract the tvshow and episode IMDN ids
    if m.group('primary_agent') ==  "com.plexapp.agents.thetvdb":
      #Fetch the IMDB episode ID
      xml = XML.ElementFromString(GetResultFromNetwork(TVDB_SERIES_URL % m.group('showID')+'/default/'+m.group('seasonID')+'/'+m.group('episodeID')), encoding='utf8')
      episodeIMDBId = xml.xpath('//Data/Episode/IMDB_ID')[0].text
      if episodeIMDBId !=None:
        episodeIMDBId = episodeIMDBId.replace('tt', '')
      
  return  episodeIMDBId
            
def getLangList():
  langList = [Prefs["langPref1"]]
  if Prefs["langPref2"] != 'None' and Prefs["langPref1"] != Prefs["langPref2"]:
    langList.append(Prefs["langPref2"])
  return langList

def logFilteredSubtitleResponseItem(item):
  #Log('Keys available: %s' % subtitleResponse[0].keys())
  #Keys available: ['ISO639', 'SubComments', 'UserID', 'SubFileName', 'SubAddDate', 'SubBad', 'SubLanguageID', 'SeriesEpisode', 'MovieImdbRating', 'SubHash', 'MovieReleaseName', 'SubtitlesLink', 'IDMovie', 'SeriesIMDBParent', 'SubDownloadsCnt', 'QueryParameters', 'MovieByteSize', 'MovieKind', 'SeriesSeason', 'IDSubMovieFile', 'SubSize', 'IDSubtitle', 'IDSubtitleFile', 'MovieFPS', 'SubSumCD', 'QueryNumber', 'SubAuthorComment', 'MovieNameEng', 'MatchedBy', 'SubHD', 'SubRating', 'SubDownloadLink', 'SubHearingImpaired', 'ZipDownloadLink', 'SubFeatured', 'MovieTimeMS', 'SubActualCD', 'UserNickName', 'SubFormat', 'MovieHash', 'LanguageName', 'UserRank', 'MovieName', 'IDMovieImdb', 'MovieYear']
  Log(' - PlexScore: %d | MovieName: %s | MovieKind: %s | SubFileName: %s | SubBad: %s | SubHearingImpaired: %s | SubRating: %s | SubDownloadsCnt: %s | IDMovie: %s | IDMovieImdb: %s | SeriesIMDBParent: %s | MovieReleaseName:%s |MovieFPS: %s | MovieTimeMS: %s | SeriesEpisode:%s' % (item['PlexScore'], item['MovieName'], item['MovieKind'], item['SubFileName'], item['SubBad'], item['SubHearingImpaired'], item['SubRating'], item['SubDownloadsCnt'], item['IDMovie'], item['IDMovieImdb'], item['SeriesIMDBParent'], item['MovieReleaseName'], item['MovieFPS'], item['MovieTimeMS'], item['SeriesEpisode']))

def logFilteredSubtitleResponse(subtitleResponse):
  #Prety way to display subtitleResponse in Logs sorted by PlexScore (and by download in case of equality)
  if subtitleResponse != False:
    Log('Current subtitleResponse has %d elements:' % len(subtitleResponse))
    tempSortedList = sorted(subtitleResponse, key=lambda k: int(k['SubDownloadsCnt']), reverse=True)
    for item in sorted(tempSortedList, key=lambda k: k['PlexScore'], reverse=True):
      logFilteredSubtitleResponseItem(item)
  else:
    Log('Current subtitleResponse is empty')
    
def fetchSubtitles(proxy, token, part, language, primaryAgentLanguage, searchMethode):
  if searchMethode == OS_Search_Methode.Hash:
    # Download OS result based on hash and size
    Log('Looking for match for GUID %s and size %d and language %s' % (part.openSubtitleHash, part.size, language))
    #TODO: is there a way to play with cachetime. Perhaps we can set is to 0 if Air date or date of adding to base < 48h
    #BUG with 503 response
    proxyResponse = proxy.SearchSubtitles(token,[{'sublanguageid':language, 'moviehash':part.openSubtitleHash, 'moviebytesize':str(part.size)}])

  elif searchMethode == OS_Search_Methode.IMDB:
    #Download OS result based on IMDB id
    #TODO: complete IMDB search
    Log('Looking for match for IMDB and language %s' % ( language))
  elif searchMethode == OS_Search_Methode.Name:
    #Download OS result based on Name
    #TODO: complete Name search
    Log('Looking for match for name and language %s' % ( language))

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

        #TODO: Idea: filter with the name of the file. Is this a good idea ? Not sure due to many users rename the files.
        #TODO: Idea: use movie duration and FPS to choose a good sub

        #filter depending on a pref on SubHearingImpaired
        #TODO: Perhaps we can filter that just before download
        #if Prefs['HearingImpairedPref'] == 'Yes' and int(sub['SubHearingImpaired'])==1:
        #  sub['PlexScore'] = sub['PlexScore'] + OS_HEARING_IMPAIRED_BONUS

        filteredSubtitleResponse.append(sub)
        #Currently the following code is useless since the OS_ORDER_PENALTY is set to 0 (waiting better default order from OS.org)
        firstScore = firstScore + OS_ORDER_PENALTY

    else:
      Log('hash/size search return no results')
      filteredSubtitleResponse = False

  return filteredSubtitleResponse
    
 
def filterSubtitleResponseForMovie(subtitleResponse, proxy, token,  media, metadata, primaryAgentLanguage):
  imdbID = metadata.id
  #TODO: this part should be done before to apply common filter on the result by imdbID
  #if subtitleResponse == False and imdbID != '': #let's try the imdbID, if we have one...
    #Log('Found nothing via hash, trying search with imdbid: ' + imdbID)
    #subtitleResponse = proxy.SearchSubtitles(token,[{'sublanguageid':l, 'imdbid':imdbID}])['data']
    #Log(subtitleResponse)

  if subtitleResponse == False:
    filteredSubtitleResponse = False
  else:
    # Apply some filter just for movie kind video file    
    filteredSubtitleResponse = []
    for sub in subtitleResponse:
      #Check type of the video file associated to the sub in OS database (movie or other)
      if sub['MovieKind']!='movie':
        sub['PlexScore']=sub['PlexScore'] + OS_WRONG_MOVIE_KIND_PENALTY

      #check if the imdbID match
      if sub['IDMovieImdb'] == metadata.id:
        sub['PlexScore'] = sub['PlexScore'] + OS_MOVIE_IMDB_MATCH_BONUS

      #Check episode name consistency only if the lengauge of the primary agent is "en" because OpenSubtitles use English titles
      if primaryAgentLanguage == "en":
        Log('MovieName: %s | media.title: %s' % (sub['MovieName'], media.title))
        if sub['MovieName'].strip().lower() == media.title.strip().lower():
          sub['PlexScore'] = sub['PlexScore'] + OS_TITLE_MATCH_BONUS
          Log('Movie Title match')

      filteredSubtitleResponse.append(sub)
    logFilteredSubtitleResponse(filteredSubtitleResponse)
  

  return filteredSubtitleResponse
  
def filterSubtitleResponseForTVShow(subtitleResponse, season, episode, metadata, media, ImdbShowId, ImdbEpisodeId, primaryAgentLanguage):
  # I can't filter on the episode number due to some difference beteween air order and DVD order.
  if subtitleResponse == False:
    filteredSubtitleResponse = False
  else:
    filteredSubtitleResponse = []
    for sub in subtitleResponse:
      #If season match add a bonus to the score
      if int(sub['SeriesSeason']) == int(season):
        sub['PlexScore'] = sub['PlexScore'] + OS_TVSHOWS_GOOD_SEASON_BONUS

      #if IMDB id match for show add a bonnus
      if ImdbShowId != False:
        if sub['SeriesIMDBParent'] == ImdbShowId:
          sub['PlexScore'] = sub['PlexScore'] + OS_TVSHOWS_SHOW_IMDB_ID_MATCH_BONUS
      #if IMDB id match for episode add a bonnus
      if ImdbEpisodeId != False:
        if sub['IDMovieImdb'] == ImdbEpisodeId:
          sub['PlexScore'] = sub['PlexScore'] + OS_TVSHOWS_EPISODE_IMDB_ID_MATCH_BONUS
      
      #Check if video type match a tvshow
      if sub['MovieKind'] != 'episode':
        sub['PlexScore']=sub['PlexScore'] + OS_WRONG_MOVIE_KIND_PENALTY

      #Check episode name consistency only if the lengauge of the primary agent is "en" because OpenSubtitles use English titles
      if primaryAgentLanguage == "en":
        Log('MovieName: %s | media (show): %s , media (episode): %s' % (sub['MovieName'], media.title, media.seasons[season].episodes[episode].title ))
        #Log(sub['MovieName'].strip().lower())
        #Log('"%s" %s' % (media.title.strip().lower(), media.seasons[season].episodes[episode].title.strip().lower()))
          
        if sub['MovieName'].strip().lower() == '"%s" %s' % (media.title.strip().lower(), media.seasons[season].episodes[episode].title.strip().lower()):
          sub['PlexScore'] = sub['PlexScore'] + OS_TITLE_MATCH_BONUS
          Log('Episode Title match')

      #Check episode number.
      #TODO: Is there a way to handle this correctly if DVD order is used ?
      if sub['SeriesEpisode'] == episode:
        Log('Episode number match')
        sub['PlexScore'] = sub['PlexScore'] + OS_TVSHOWS_GOOD_EPISODE_BONUS

      filteredSubtitleResponse.append(sub)

    logFilteredSubtitleResponse(filteredSubtitleResponse)
  return filteredSubtitleResponse

def downloadBestSubtitle(subtitleResponse, part, language):
  #Suppress all subtitle format no supported and subtitle with score under the qualification trigger
  if subtitleResponse != False:
      #Change the way of filterin because subtitleResponse.remove doesn't work well in this case
      filteredSubtitleResponse = []
      for st in subtitleResponse: #remove any subtitle formats we don't recognize
        if st['SubFormat'] not in subtitleExt:
          Log('Removing a subtitle of type: ' + st['SubFormat'])
        elif st['PlexScore'] < OS_ACCEPTABLE_SCORE_TRIGGER: #remove any subtitle with score under the acceptable trigger
          Log('Removing a subtitle with score(%d) under the acceptable trigger (%d)' % (st['PlexScore'], OS_ACCEPTABLE_SCORE_TRIGGER))
          #TODO: Perhaps it could be a good idea to use API to ask OS to remove bad subs. those with a score < very low score (about 900)
        else:
          filteredSubtitleResponse.append(st)
      subtitleResponse = filteredSubtitleResponse
  #BUG : UnboundLocalError: local variable 'filteredSubtitleResponse' referenced before assignment

  if subtitleResponse != False:
  #Download the sub with the higest PlexScore in the filtered list.
  #TODO: Perhaps HearingImpaired choice have to be done here
  #TODO: Perhaps it is possible to chose more than one sub.
    #To process equality on PlexScore, first order with the download count
    tempSortedList = sorted(filteredSubtitleResponse, key=lambda k: int(k['SubDownloadsCnt']), reverse=True)
    # The best subtitle is the ons with the best PlexScore
    st = sorted(tempSortedList, key=lambda k: k['PlexScore'], reverse=True)[0]
    Log('Best subtitle is:')
    logFilteredSubtitleResponseItem(st)
    subUrl = st['SubDownloadLink']
    subGz = HTTP.Request(subUrl, headers={'Accept-Encoding':'gzip'}).content
    subData = Archive.GzipDecompress(subGz)
    # TODO : Supression of previous sub should be there to avoid wiping a sub not anymore in OS
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
    if token == False:
      Log('Subtitles search stop due to a problem with the OpenSubtitles API')
    else:
      for i in media.items:
        primaryAgentLanguage = getLanguageOfPrimaryAgent(media.guid)
        Log("Movie: %s, id:%s, primaryAgentLanguage: %s" % (media.title, media.id, primaryAgentLanguage))
        for part in i.parts:
          # Remove all previous subs (taken from sender1 fork)
          for l in part.subtitles:
            part.subtitles[l].validate_keys([])

          # go fetch subtilte fo each language
          for language in getLangList():
            subtitleResponse = fetchSubtitles(proxy, token, part, language, primaryAgentLanguage, OS_Search_Methode.Hash)
            subtitleResponse = filterSubtitleResponseForMovie(subtitleResponse, proxy, token, media, metadata, primaryAgentLanguage)
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
    if token == False:
      Log('Subtitles search stop due to a problem with the OpenSubtitles API')
    else:
      #BUG: this search in metadata agent return no result an in the web search there are results
      #http://www.opensubtitles.org/fr/search/sublanguageid-eng/moviebytesize-259882514/moviehash-330999989ae4f902
      ImdbShowId = getImdBShowIdfromTheTVDB(media.guid)
      for season in media.seasons:
        # just like in the Local Media Agent, if we have a date-based season skip for now.
        if int(season) < 1900:
          for episode in media.seasons[season].episodes:
            for i in media.seasons[season].episodes[episode].items:
              Log("Show: %s, Season: %s, Ep: %s, id:%s" % (media.title, season, episode, media.seasons[season].episodes[episode].id))
              Log("GUID episode: %s" % media.seasons[season].episodes[episode].guid)
              ImdbEpisodeId = getImdBEpisodeIdfromTheTVDB(media.seasons[season].episodes[episode].guid)
              primaryAgentLanguage = getLanguageOfPrimaryAgent(media.seasons[season].episodes[episode].guid)
              Log('ImdbShowId: %s | ImdbEpisodeId: %s | primaryAgentLanguage: %s' % (ImdbShowId, ImdbEpisodeId, primaryAgentLanguage))
              for part in i.parts:
                # Remove all previous subs (taken from sender1 fork)
                for l in part.subtitles:
                  part.subtitles[l].validate_keys([])

                # go fetch subtilte fo each language
                for language in getLangList():
                  subtitleResponse = fetchSubtitles(proxy, token, part, language, primaryAgentLanguage, OS_Search_Methode.Hash)
                  subtitleResponse = filterSubtitleResponseForTVShow(subtitleResponse, season, episode, metadata, media, ImdbShowId, ImdbEpisodeId, primaryAgentLanguage)
                  downloadBestSubtitle(subtitleResponse, part, language)
                    
