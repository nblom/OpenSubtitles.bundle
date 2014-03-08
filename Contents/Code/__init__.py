#opensubtitles.org
#Subtitles service allowed by www.OpenSubtitles.org

OS_API = 'http://plexapp.api.opensubtitles.org/xml-rpc'
OS_LANGUAGE_CODES = 'http://www.opensubtitles.org/addons/export_languages.php'
OS_PLEX_USERAGENT = 'plexapp.com v9.0'
#OS_PLEX_USERAGENT = 'OS Test User Agent'
subtitleExt       = ['utf','utf8','utf-8','sub','srt','smi','rt','ssa','aqt','jss','ass','idx']
 
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

def logSubtitleResponse(subtitleResponse):
  #Prety way to display subtitleResponse in Logs
  Log('Current subtitleResponse has %d elements:' % len(subtitleResponse))
  for item in subtitleResponse:
    Log(' - MovieName: %s | MovieYear: %s | MovieNameEng: %s | SubAddDate: %s | SubBad: %s | SubRating: %s | SubDownloadsCnt: %s | IDMovie: %s | IDMovieImdb: %s' % (item['MovieName'], item['MovieYear'], item['MovieNameEng'], item['SubAddDate'], item['SubBad'], item['SubRating'], item['SubDownloadsCnt'], item['IDMovie'], item['IDMovieImdb']))

def fetchSubtitles(proxy, token, part, language):

  # Remove all previous subs (taken from sender1 fork)
  for l in part.subtitles:
    part.subtitles[l].validate_keys([])

  Log('Looking for match for GUID %s and size %d and language %s' % (part.openSubtitleHash, part.size, language))
  #subtitleResponse = proxy.SearchSubtitles(token,[{'sublanguageid':language, 'moviehash':part.openSubtitleHash, 'moviebytesize':str(part.size)}])['data']
  proxyResponse = proxy.SearchSubtitles(token,[{'sublanguageid':language, 'moviehash':part.openSubtitleHash, 'moviebytesize':str(part.size)}])
  if proxyResponse['status'] != "200 OK":
    Log('Error return by XMLRPC proxy: %s' % proxyResponse['status'])
    subtitleResponse = False
  else:
    subtitleResponse = proxyResponse['data']
    Log('hash/size search result: ')
    logSubtitleResponse(subtitleResponse)
  
  return subtitleResponse
    
 
def filterSubtitleResponseForMovie(subtitleResponse, proxy, token, metadata):
  imdbID = metadata.id
  if subtitleResponse == False and imdbID != '': #let's try the imdbID, if we have one...
    Log('Found nothing via hash, trying search with imdbid: ' + imdbID)
    subtitleResponse = proxy.SearchSubtitles(token,[{'sublanguageid':l, 'imdbid':imdbID}])['data']
    #Log(subtitleResponse)

    #I don't know if I can filter on the name of the movie due to some metadata agent return Movie name in an other language.

    return subtitleResponse
  
def filsterSubtitleResponseForTVShow(subtitleResponse):
  #I don't know if I can filter on the tvshow name as some metadata agent return TBVShow name in other language.



  return subtitleResponse

def downloadBestSubtitle(subtitleResponse, part, language):
  #Suppress all subtitle format no supported
  if subtitleResponse != False:
      for st in subtitleResponse: #remove any subtitle formats we don't recognize
        if st['SubFormat'] not in subtitleExt:
          Log('Removing a subtitle of type: ' + st['SubFormat'])
          subtitleResponse.remove(st)
  if subtitleResponse != False:
  #Download the most downloaded sub in the filtered list.
    st = sorted(subtitleResponse, key=lambda k: int(k['SubDownloadsCnt']), reverse=True)[0] #most downloaded subtitle file for current language
    subUrl = st['SubDownloadLink']
    subGz = HTTP.Request(subUrl, headers={'Accept-Encoding':'gzip'}).content
    subData = Archive.GzipDecompress(subGz)
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
      for part in i.parts:
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
    for s in media.seasons:
      # just like in the Local Media Agent, if we have a date-based season skip for now.
      if int(s) < 1900:
        for e in media.seasons[s].episodes:
          for i in media.seasons[s].episodes[e].items:
            for part in i.parts:
              for language in getLangList():
                subtitleResponse = fetchSubtitles(proxy, token, part, language)
                subtitleResponse = filsterSubtitleResponseForTVShow(subtitleResponse)
                downloadBestSubtitle(subtitleResponse, part, language)
                  
