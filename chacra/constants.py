# a list of distro versions that chacra will generate a distributions file for
DISTRIBUTIONS = [
    'sid',
    'stretch',
    'jessie',
    'wheezy',
    'squeeze',
    'precise',
    'quantal',
    'saucy',
    'trusty',
    'utopic',
    'vivid',
    'wily',
    'xenial',
]

# These are reserved keys that will be ignored when processing repos. Otherwise
# they would be treated as refs.
REPO_OPTION_KEYS = (
    'combined',
    'automatic',
)
