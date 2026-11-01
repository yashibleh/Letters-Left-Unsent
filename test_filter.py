"""Try the filter on sample letters.   Run from the backend folder with the venv active:  python test_filter.py
'ok' = you expect it to be pinned, 'block' = you expect the gentle popup. Edit SAMPLES freely - these are guesses.
Too many kind letters blocked?  raise TOPIC_THRESHOLD / TOXIC_THRESHOLD.  Politics or insults slipping through?  lower them."""
import time
import ml_filter as mf

SAMPLES = [
    ("ok", "Thank you for driving me to school every morning. I never said how much it meant to me."),
    ("ok", "Grandma, I still make your tea the way you did, with too much sugar. I miss you every single day."),
    ("ok", "I'm sorry I was so distant last year. I was struggling, and I took it out on you. You deserved better."),
    ("ok", "To my best friend: you stayed up all night with me before my exam and never once complained. Thank you."),
    ("ok", "Dear coach, you taught me that losing is just practice for winning. I think of that every morning."),
    ("ok", "My gay brother was the first person who believed in me. I never thanked him properly, so: thank you."),
    ("ok", "My Muslim neighbour brought food when dad was in hospital. I will never forget that kindness."),
    ("ok", "I was angry at you for a long time, but I understand now. I hope you are happy wherever you are."),
    ("ok", "To the stranger who returned my wallet at the bus stop: you restored my faith in people."),
    ("ok", "Dear teacher, you were strict, and I hated it then. Now I know it is why I can write. Thank you."),
    ("ok", "Papa, I know you never say it, but I see how hard you work. I hope to make you proud."),
    ("ok", "We lost the match, but standing on that pitch with all of you was the best day of my year."),
    ("block", "I hate you. You are a stupid, worthless idiot and everyone knows it."),
    ("block", "Honestly, I hope something terrible happens to you. You deserve every bit of it."),
    ("block", "Shut up, you disgusting loser. Nobody wants you around."),
    ("block", "The government is lying to us and the election was stolen. Wake up, sheeple!"),
    ("block", "Vote for the other party and this country is finished. Their leader is a criminal."),
    ("block", "Liberals and conservatives are both ruining everything. Here is why my side is right."),
    ("block", "Did you hear what Priya did at the party? Everyone is talking about it, she is such a fake."),
    ("block", "I have to tell you the gossip about our neighbour. She is cheating and everybody knows."),
    ("block", "Thanks for nothing. Maybe next time you could actually think about someone besides yourself."),
    ("block", "Dear ex, I hope your new life is as empty as you made mine. Enjoy being alone."),
    ("block", "This religion is a scam and anyone who follows it is brainwashed. Prove me wrong."),
    ("block", "Abortion should be banned. Anyone who disagrees is a murderer. Debate me."),
]

def main():
    t = time.time(); mf.load_models(); print(f"models ready in {time.time() - t:.1f}s\n")
    wrong = []
    for expect, text in SAMPLES:
        t = time.time(); r = mf.check_text(text, full=True); ms = (time.time() - t) * 1000
        got = "ok" if r["approved"] else "block"
        top = ", ".join(f"{k}={v}" for k, v in sorted(r["scores"].items(), key=lambda kv: -kv[1])[:3])
        print(f"[{got:5}] expected {expect:5} {ms:4.0f} ms  {text[:58]!r}\n         top scores: {top}" + ("   <-- MISMATCH" if got != expect else ""))
        if got != expect: wrong.append((expect, text))
    blocked_kind = [t for e, t in wrong if e == "ok"]; missed = [t for e, t in wrong if e == "block"]
    print(f"\n{len(SAMPLES) - len(wrong)}/{len(SAMPLES)} as expected.  Kind letters wrongly blocked: {len(blocked_kind)}.  Harmful letters let through: {len(missed)}.")

if __name__ == "__main__":
    main()
