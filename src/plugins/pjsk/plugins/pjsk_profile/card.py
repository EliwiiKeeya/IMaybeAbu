from io import BytesIO

from PIL import Image, ImageDraw, ImageFont

from .models import PJSKProfileContentBase

assets = "src/plugins/pjsk/plugins/pjsk_profile/assets"


class PJSKProfileCard(BytesIO):
    def __init__(self, profile: PJSKProfileContentBase):
        # 读取卡片资源
        img = Image.open(
            f"{assets}/card.png")
        draw = ImageDraw.Draw(img)

        # 绘制用户名
        font_style = ImageFont.truetype(
            f"{assets}/SourceHanSansCN-Bold.otf", 45)
        draw.text(
            (295, 45),
            profile.user.name,
            fill=(0, 0, 0),
            font=font_style
        )

        # 绘制用户ID
        font_style = ImageFont.truetype(
            f"{assets}/FOT-RodinNTLGPro-DB.ttf", 20)
        draw.text(
            (298, 116),
            'id:' + str(profile.user.userId),
            fill=(0, 0, 0),
            font=font_style
        )

        # 绘制用户等级
        font_style = ImageFont.truetype(
            f"{assets}/FOT-RodinNTLGPro-DB.ttf", 34)
        draw.text(
            (415, 157),
            str(profile.user.rank),
            fill=(255, 255, 255),
            font=font_style
        )

        # 绘制用户经验值
        font_style = ImageFont.truetype(
            f"{assets}/FOT-RodinNTLGPro-DB.ttf", 22)
        draw.text(
            (182, 318),
            str(profile.userProfile.twitterId),
            fill=(0, 0, 0),
            font=font_style
        )

        # 绘制用户签名
        font_style = ImageFont.truetype(
            f"{assets}/SourceHanSansCN-Medium.otf", 24)
        size = font_style.getlength(profile.userProfile.word)
        if size > 480:
            draw.text(
                (132, 388),
                profile.userProfile.word[:int(
                    len(profile.userProfile.word) * (460 / size)
                )],
                fill=(0, 0, 0),
                font=font_style
            )
            draw.text(
                (132, 424),
                profile.userProfile.word[int(
                    len(profile.userProfile.word) * (460 / size)
                ):],
                fill=(0, 0, 0),
                font=font_style
            )
        else:
            draw.text(
                (132, 388),
                profile.userProfile.word,
                fill=(0, 0, 0),
                font=font_style
            )

        # 绘制 Easy ~ Master 统计数据
        font_style = ImageFont.truetype(
            f"{assets}/FOT-RodinNTLGPro-DB.ttf", 24)
        text_height = font_style.size / 2 + 1
        for i, item in enumerate(profile.userMusicDifficultyClearCount[:5]):
            # clear
            text_width = font_style.getlength(str(item.liveClear))
            text_coordinate = (
                int(167 + 105 * i - text_width / 2),
                int(732 - text_height)
            )
            draw.text(
                text_coordinate,
                str(item.liveClear),
                fill=(0, 0, 0),
                font=font_style
            )

            # full combo
            text_width = font_style.getlength(str(item.fullCombo))
            text_coordinate = (
                int(167 + 105 * i - text_width / 2),
                int(732 + 133 - text_height)
            )
            draw.text(
                text_coordinate,
                str(item.fullCombo),
                fill=(0, 0, 0),
                font=font_style
            )

            # all perfect
            text_width = font_style.getlength(str(item.allPerfect))
            text_coordinate = (
                int(167 + 105 * i - text_width / 2),
                int(732 + 2 * 133 - text_height)
            )
            draw.text(
                text_coordinate,
                str(item.allPerfect),
                fill=(0, 0, 0),
                font=font_style
            )

        # 绘制 Append 难度统计数据
        item = profile.userMusicDifficultyClearCount[5]
        text_width = font_style.getlength(str(item.liveClear))

        # clear
        text_coordinate = (
            int(707 - text_width / 2),
            int(732 - text_height)
        )
        draw.text(
            text_coordinate,
            str(item.liveClear),
            fill=(0, 0, 0),
            font=font_style
        )

        # full combo
        text_width = font_style.getlength(str(item.fullCombo))
        text_coordinate = (
            int(707 - text_width / 2),
            int(732 + 133 - text_height)
        )
        draw.text(
            text_coordinate,
            str(item.fullCombo),
            fill=(0, 0, 0),
            font=font_style
        )

        # all perfect
        text_width = font_style.getlength(str(item.allPerfect))
        text_coordinate = (
            int(707 - text_width / 2),
            int(732 + 2 * 133 - text_height)
        )
        draw.text(
            text_coordinate,
            str(item.allPerfect),
            fill=(0, 0, 0),
            font=font_style
        )

        # 绘制世界团体角色等级
        character_id = 1
        font_style = ImageFont.truetype(
            f"{assets}/FOT-RodinNTLGPro-DB.ttf", 29)
        for i in range(0, 5):
            for j in range(0, 4):
                characterRank = profile.userCharacters[character_id -
                                                       1].characterRank
                text_width = font_style.getlength(str(characterRank))
                text_coordinate = (
                    int(916 + 184 * j - text_width / 2),
                    int(688 + 87.5 * i - text_height)
                )
                draw.text(text_coordinate, str(characterRank),
                          fill=(0, 0, 0), font=font_style)

                character_id += 1

        # 绘制虚拟歌手角色等级
        for i in range(0, 2):
            for j in range(0, 4):
                characterRank = profile.userCharacters[character_id -
                                                       1].characterRank
                text_width = font_style.getlength(str(characterRank))
                text_coordinate = (
                    int(916 + 184 * j - text_width / 2),
                    int(512 + 88 * i - text_height)
                )
                draw.text(text_coordinate, str(characterRank),
                          fill=(0, 0, 0), font=font_style)
                character_id = character_id + 1
                if character_id == 27:
                    break

        # 绘制 Mvp 和 Super Star 统计数据
        draw.text(
            (952, 141),
            f'{profile.userMultiLiveTopScoreCount.mvp}回',
            fill=(0, 0, 0),
            font=font_style
        )
        draw.text(
            (1259, 141),
            f'{profile.userMultiLiveTopScoreCount.superStar}回',
            fill=(0, 0, 0),
            font=font_style
        )

        # 绘制挑战 Live 结果
        draw.text(
            (1032, 315),
            str(profile.userChallengeLiveSoloResult.highScore),
            fill=(0, 0, 0),
            font=font_style
        )

        # 保存图片到 BytesIO
        super().__init__()
        img.save(self, format='PNG')
