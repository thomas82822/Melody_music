#
# Copyright (C) 2021-2022 by TheY_CaIl_mE_OG@Github, < https://github.com/TheY_CaIl_mE_OG >.
#
# This file is part of < https://github.com/thomas82822/Melody_music > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/thomas82822/Melody_music/blob/master/LICENSE >
#
# All rights reserved.

from MelodiX.core.bot import MelodiXBot
from MelodiX.core.dir import dirr
from MelodiX.core.git import git
from MelodiX.core.userbot import Userbot
from MelodiX.misc import dbb, heroku, sudo

from .logging import LOGGER

# Directories
dirr()

# Check Git Updates
git()

# Initialize Memory DB
dbb()

# Heroku APP
heroku()

# Load Sudo Users from DB
sudo()

# Bot Client
app = MelodiXBot()

# Assistant Client
userbot = Userbot()

from .platforms import *

YouTube = YouTubeAPI()
Carbon = CarbonAPI()
Telegram = TeleAPI()
