# v004 — iPhone-12 4s, "smooth" skin (ANTI-PATTERN / negative result)
# Tested in the authoring session. Near-isolated sibling of v001: same iPhone-12 raw-UGC base, but
# skin.strategy=smooth ("naturally smooth, healthy, even skin") instead of real_microtexture.
# Comment (user): "the skin is smooth as in texture is really ai like ... avoid unrealistic ai texture
# skin". Kept here as the counter-example that proves p001. DO NOT use "smooth" for skin.

<cpcs model="veo-3.1" mode="i2v" aspect="9:16" fps="30" render_s="4" trim_s="4" style="raw_ugc_iphone12">
  <control lang="yaml"><![CDATA[
device: iPhone 12 front camera; 1080p; 30fps (not filmic); smart_hdr flat tone; cool white balance; apple noise-reduction; light oversharpen; floaty builtin stabilization w/ micro-jitter; AF & exposure breathe; deep focus, NO bokeh
look: ordinary real iPhone selfie, NOT cinematic, not an ad. Black woman early 30s, warm brown skin, minimal makeup, hair in a messy claw clip with a few flyaways, plain grey tee. Normal home bathroom, plain background, everyday clutter. Flat overhead indoor light. Phone held a bit too close, slightly below eye level, mild wide-angle distortion.
skin: naturally smooth, healthy, even skin with soft subtle texture and a light natural sheen; realistic but not exaggerated — no heavy pores, no rough patches, no oily shine; still NOT airbrushed or plastic.   # <-- THIS PHRASING RENDERED AS AI/WAXY SKIN. See p001.
face_motion: alive and constantly, subtly moving — natural eye movement and small darts, gentle blinks, tiny brow flickers, soft cheek and lip micro-shifts, natural talking mouth shapes, small head bobs in sync with speech; relaxed, casual, expressive but low-key, never stiff or frozen.
perform: casual, telling-a-friend energy, low-key, not performing; a small shrug; one quick glance off to the side then back.
say: "Always tired but don't wanna live on caffeine? This actually helped." brisk and natural, small breath first, ending on a small easy half-smile.
audio: close, slightly boomy iPhone front-mic; room echo; faint hum; no music.
forbid: beauty_smoothing, plastic_skin, exaggerated_pores, bokeh, cinematic_grade, 24fps_film_look, glam_lighting, frozen_stiff_face.
]]></control>
  <render>no on-screen text, no subtitles, no product in frame</render>
</cpcs>
