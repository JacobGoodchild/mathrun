# Setting up mathrun on your Linux Mint computer

Everything below is typed into a **Terminal** (Menu → Terminal). Lines starting with `#` are comments; you don't need to type them. Nothing here needs `sudo` except the one optional `apt` line in step 2.

## 1. Get the code

```bash
cd ~
git clone https://github.com/JacobGoodchild/mathrun.git
cd mathrun
```

(If you'd rather not keep it in your home folder, clone it anywhere. mathrun only ever writes inside its own folder.)

## 2. Check the tools (one-off)

```bash
./mathrun install
```

This checks for Python 3, `gcc` and `make`, builds every searcher, and creates your personal settings file `config.local.toml`.

If it says something is missing, it prints the exact line to run, which is:

```bash
sudo apt install build-essential python3
```

Optional, but it makes the big-number searchers (perfect cuboid, Beal) faster:

```bash
sudo apt install libgmp-dev
./mathrun install      # run it again so it picks GMP up
```

Without `libgmp-dev`, mathrun uses its own built-in copy of mini-gmp. Everything still works, just a little slower.

## 3. Prove it works

```bash
./mathrun selftest
```

This runs every test: each searcher must re-find famous known answers (Strassen's 7 multiplications, the 33 and 42 three-cube solutions, Brocard's 4, 5 and 7, and so on). It then does a short trial run of each searcher, and checks that each independent checker accepts real answers and rejects deliberately damaged ones. It should finish in about a minute and end with **SELFTEST PASSED**.

## 4. Start searching

```bash
./mathrun start
```

That's it. The searchers run in the background at the lowest priority, so anything you do comes first. By default they use every core but one. They pause by themselves if the CPU gets hotter than 85 °C, and carry on when it cools down.

## 5. Watch the dashboard

```bash
./mathrun dashboard
```

This opens `http://127.0.0.1:8471/` in your browser. Only your own computer can see it. Close the terminal window (or press Ctrl-C) to close the dashboard; the searchers keep going.

For a quick text summary instead:

```bash
./mathrun status
```

## Everyday controls

| You want to… | Type |
|---|---|
| Pause everything (gaming, video calls…) | `./mathrun gaming on` |
| Carry on again | `./mathrun gaming off` |
| Stop and save | `./mathrun stop` |
| Start again later (carries on where it stopped) | `./mathrun start` |

Turning the computer off without stopping first is fine too. Progress is saved after every work unit (every few minutes) in a way that can't be corrupted. At most a few minutes of work are lost.

### Changing settings

Open `config.local.toml` in a text editor (for example `xed config.local.toml`). The settings are explained in the file. The useful ones:

- `workers`: how many cores to use (0 = all but one).
- `max_temp_c`: the temperature that triggers a pause (default 85).
- `only_when_idle = true`: only search when you haven't touched the keyboard or mouse for `idle_seconds`. For reliable idle detection on Cinnamon, install the small `xprintidle` tool (`sudo apt install xprintidle`). If mathrun can't tell whether you're idle, it plays safe and stays paused; `./mathrun status` shows "only-when-idle mode, but idle time can't be read" if that happens.
- `pause_for_programs = ["steam_app"]`: pause automatically while certain programs run.
- `[problems] skip = ["collatz"]`: don't run a problem. `[problems.weights]` gives a problem more or less CPU time.

After editing, run `./mathrun stop` then `./mathrun start`.

## Start automatically when you log in (optional)

```bash
./mathrun add-autostart
```

This creates one small file, `~/.config/systemd/user/mathrun.service`. It's the only file mathrun ever puts outside its own folder. To undo it:

```bash
./mathrun remove-autostart
```

## Phone or email alert (optional)

If a searcher ever finds something that passes the independent check, you get a desktop pop-up anyway. To also get a phone notification:

1. Install the free **ntfy** app (Android or iPhone) and subscribe to a topic with a long, hard-to-guess name, like `mathrun-jacob-7f3k9q2x`.
2. In `config.local.toml`, under `[alerts]`, set `ntfy_topic = "mathrun-jacob-7f3k9q2x"`.
3. For an email as well, set `ntfy_email = "you@example.com"`.
4. Restart: `./mathrun stop`, then `./mathrun start`.

The message only ever says the problem name and "candidate verified, check dashboard". `config.local.toml` is never uploaded to GitHub.

## Publish the dashboard on the web (optional, off by default)

This puts a small status snapshot (under 1 MB of JSON) on GitHub Pages, so you can check progress from your phone. It pushes **at most once an hour**, and only while the computer is on. It never uploads logs or checkpoints, and uses no GitHub Actions.

1. Make sure `git push` works from this folder without a password prompt. GitHub's guide to SSH keys covers this, or you can use a stored token.
2. On GitHub: open the repository → **Settings** → **Pages** → **Build and deployment** → Source: **Deploy from a branch** → Branch: **main**, folder **/docs** → Save.
3. In `config.local.toml`, under `[publish]`, set `enabled = true`.
4. Try it once by hand: `./mathrun publish`. After that, the runner does it by itself every hour.
5. Your dashboard will be at `https://jacobgoodchild.github.io/mathrun/`.

## If something is found

The dashboard shows a red **VERIFIED CANDIDATE — needs human review** banner, and you get the alerts above. Remember what that means: two separate programs agree, by computer, that it checks out. It is not a proof. Look at the candidate (click the problem on the dashboard), keep a copy of `data/candidates/`, and ask an expert before telling the world.

If a searcher ever reports something the checker *rejects*, that searcher is paused as "possible searcher bug" so it can't waste time. Once you've looked, `./mathrun clear-bug <problem-name>` lets it run again.

## Uninstall

```bash
cd ~/mathrun
./mathrun stop
./mathrun remove-autostart
cd ~
rm -rf ~/mathrun
```

That removes everything: code, settings, checkpoints and logs.
