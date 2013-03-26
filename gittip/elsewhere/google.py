import datetime
import gittip
import hashlib
import requests
from aspen import json, log, Response
from aspen.utils import to_age, utc, typecheck
from aspen.website import Website
from gittip.elsewhere import AccountElsewhere, ACTIONS, _resolve, AuthorizationError


class GoogleProvider(AccountElsewhere):
    service_name = 'google'
    oauth_cache = {}

    def __init__(self, website, username=None, ):
        if username is None:
            log(response)
        super(GoogleProvider, self).__init__(username, website)

    def get_oauth_init_url(self, next='', action=u'opt-in'):
        nonce = hashlib.md5(datetime.datetime.now().isoformat()).hexdigest()

        state = ','.join((self.username, nonce, action))

        self.oauth_cache[self.username] = nonce

        return ''.join([
            "https://accounts.google.com/o/oauth2/auth",
            "?response_type=code",
            "&client_id=%s",
            "&redirect_uri=%s",
            "&state=%s",
            "&scope=https://www.googleapis.com/auth/userinfo.profile",
            "&approval_prompt=force" # Force re-approval
        ]) % (self.website.google_client_id, next or 'associate', state)

    @classmethod
    def associate(cls, website, query_string):
        # pull info out of the querystring
        username, nonce, action = query_string['state'].split(',')

        # Make sure this is a supported action
        if action not in ACTIONS:
            raise Response(400)

        # Make sure the nonces match our cache
        if nonce != cls.oauth_cache.get(username): #TODO: Make this a pop
            raise AuthorizationError('Nonces do not match.')

        # Verify by exchanging the temporary token for a persistent one.
        response = requests.post(
            'https://accounts.google.com/o/oauth2/token',
            data={
                'code': query_string.get('code'),
                'client_id': website.google_client_id,
                'client_secret': website.google_client_secret,
                'grant_type': 'authorization_code',
                'redirect_uri': 'http://localhost:8537/on/google/associate'
            }
        )

        if response.status_code != 200:
            raise AuthorizationError('Failed to confirm authorization with Google.')

        user = cls(website, username)

        if action == 'opt-in':
            user.opt_in()









    def _get_user_info(self):
        typecheck(self.username, unicode)

        # Check to see if we've already imported these details
        rec = gittip.db.fetchone( "SELECT user_info FROM elsewhere "
                                  "WHERE platform='google' "
                                  "AND user_info->'screen_name' = %s"
                                , (self.username,)
                                 )
        if rec:
            # Use the record we have
            user_info = rec['user_info']
        else:
            # Call the service's API
            url = 'https://www.googleapis.com/plus/v1/people/%s?key=AIzaSyDFwxAtyIPi08FgI58rMsL5A9CqvL3kOaY'
            response = requests.get(url % self.username)

            # Make sure we got back a valid response
            if response.status_code != 200:
                log("Google user lookup failed with %d." % response.status_code)
                raise Response(404)


            external_user = json.loads(response.text)
            self._user_info = external_user

            # Get the user's avatar URL on the outside service.
            # Google's includes a ?sz=50 arg, which makes it really small.
            # We strip that out.
            self.avatar = external_user['image']['url'].split('?')[0]
            self.display_name = external_user['displayName']