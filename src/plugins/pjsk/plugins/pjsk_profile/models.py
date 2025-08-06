import requests
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel


class User(BaseModel):
    userId: int
    name: str
    rank: int

class UserProfile(BaseModel):
    userId: int
    word: str
    twitterId: str
    profileImageType: str

class UserDeck(BaseModel):
    deckId: Optional[int] = None
    userId: Optional[int] = None
    name: str
    leader: int
    subLeader: int
    member1: int
    member2: int
    member3: int
    member4: int
    member5: int

class UserCard(BaseModel):
    cardId: int
    level: int
    masterRank: int
    specialTrainingStatus: str
    defaultImage: str

class UserCharacter(BaseModel):
    characterId: int
    characterRank: int

class UserChallengeLiveSoloResult(BaseModel):
    characterId: int
    highScore: int

class UserChallengeLiveSoloStage(BaseModel):
    characterId: int
    rank: int

class UserMusicDifficultyClearCount(BaseModel):
    musicDifficultyType: str
    liveClear: int
    fullCombo: int
    allPerfect: int

class UserCustomProfileCard(BaseModel):
    # No fields in examples, keep as placeholder
    pass

class UserProfileHonor(BaseModel):
    seq: int
    profileHonorType: str
    honorId: int
    honorLevel: int
    bondsHonorViewType: str
    bondsHonorWordId: int

class UserHonor(BaseModel):
    honorId: int
    level: int

class UserBondsHonor(BaseModel):
    bondsHonorId: int
    level: int

class UserStoryFavorite(BaseModel):
    # No fields in examples, keep as placeholder
    pass

class UserConfig(BaseModel):
    friendRequestScope: str

class UserMultiLiveTopScoreCount(BaseModel):
    mvp: int
    superStar: int

class TotalPower(BaseModel):
    totalPower: int
    basicCardTotalPower: int
    areaItemBonus: int
    characterRankBonus: int
    honorBonus: int
    mysekaiGateLevelBonus: Optional[int] = None
    mysekaiFixtureGameCharacterPerformanceBonus: Optional[int] = None

class UserHonorMission(BaseModel):
    honorMissionType: str
    progress: int

class PJSKProfileContentBase(BaseModel):
    user: User
    userProfile: UserProfile
    userDeck: UserDeck
    userCards: List[UserCard]
    userCharacters: List[UserCharacter]
    userChallengeLiveSoloResult: UserChallengeLiveSoloResult
    userChallengeLiveSoloStages: List[UserChallengeLiveSoloStage]
    userMusicDifficultyClearCount: List[UserMusicDifficultyClearCount]
    userCustomProfileCards: List[UserCustomProfileCard]
    userProfileHonors: List[UserProfileHonor]
    userHonors: List[UserHonor]
    userBondsHonors: List[UserBondsHonor]
    userStoryFavorites: List[UserStoryFavorite]
    userConfig: UserConfig
    userMultiLiveTopScoreCount: UserMultiLiveTopScoreCount
    totalPower: TotalPower
    userHonorMissions: List[UserHonorMission]


class PJSKProfileContentCN(PJSKProfileContentBase):
    pass


class PJSKProfileContentTW(PJSKProfileContentBase):
    pass


class PJSKProfileContentJP(PJSKProfileContentBase):
    isMysekaiOwnerAcceptVisit: bool


class PJSKProfileBase(ABC):
    base_url: str = ""
    headers: Optional[dict] = None

    def __init__(self):
        if self.base_url == "":
            raise ValueError("Base_url must be set.")

    @abstractmethod
    def get_profile(self, user_id: str) -> PJSKProfileContentBase:
        pass


class PJSKProfileCN(PJSKProfileBase):
    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers
        super().__init__()

    def get_profile(self, user_id: str) -> Optional[PJSKProfileContentCN]:
        url = f"{self.base_url}/cn/user/{user_id}/profile"
        content = requests.get(url, headers=self.headers)
        if content.ok:
            content = content.json()
            return PJSKProfileContentCN(**content)
        else:
            return None


class PJSKProfileTW(PJSKProfileBase):
    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers
        super().__init__()

    def get_profile(self, user_id: str) -> Optional[PJSKProfileContentTW]:
        url = f"{self.base_url}/tw/user/{user_id}/profile"
        content = requests.get(url, headers=self.headers)
        if content.ok:
            content = content.json()
            return PJSKProfileContentTW(**content)
        else:
            return None


class PJSKProfileJP(PJSKProfileBase):
    def __init__(self, base_url: str, headers: Optional[dict] = None):
        self.base_url = base_url
        self.headers = headers
        super().__init__()

    def get_profile(self, user_id: str) -> Optional[PJSKProfileContentJP]:
        url = f"{self.base_url}/jp/user/%25user_id/{user_id}/profile"
        content = requests.get(url, headers=self.headers)
        if content.ok:
            content = content.json()
            return PJSKProfileContentJP(**content)
        else:
            return None
