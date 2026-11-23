# crypto_MCMC — Project Summary

University project (BUT3, Maths module) on **classical cryptography and its attacks**, ending with an **MCMC (Metropolis–Hastings) attack** on substitution and permutation ciphers. Language: **Python 3, standard library only** (except `utils/stats.py`, which uses `requests`). All code, comments and identifiers are in **French**.

## Course deliverables (from `rendu.txt`)
- Next session: a design document for part 1.5.
- End of November: a full written report, the code, and an individual oral exam showing (1) one original working feature, and (2) the attack used in realistic conditions.

## Repository layout

```
crypto_MCMC/
├── chiffrements/              # Basic ciphers + frequency analysis
│   ├── chiffrement_cesar.py
│   ├── chiffrement_vigenere.py
│   └── attaque_frequentielle.py
├── substitution/
│   └── cryptogramme.py        # Caesar wrapper: encrypt / decrypt / frequency attack
├── permutation/
│   ├── bloc.py                # Block position-permutation cipher (part 1.4)
│   └── cryptogramme.py        # Vigenère + position permutation, keyed by a word
├── utils/
│   ├── stats.py               # Wikipedia text → letter/digram stats → Markov matrix → text generator (CLI)
│   └── app.py                 # Same thing + all ciphers/attacks in a local web UI
├── mcmc/                      # MCMC attack (parts 1.3 & 1.4)
│   ├── main.py                # MCMC engine + CLI (modes: lettres / positions)
│   ├── chiffrer.py            # Generates test ciphertexts with a random/known key
│   ├── utils/
│   │   ├── score.py           # Text normalisation, bigram counts, score S(k)
│   │   ├── initialisation.py  # Initial keys (random / frequency heuristic)
│   │   ├── mutation.py        # Proposal moves (swap letters / move a sub-block)
│   │   ├── selection.py       # Metropolis acceptance rule
│   │   └── substitution.py    # Monoalphabetic substitution (26 letters)
│   ├── tests/test_mcmc.py     # unittest suite
│   ├── reference.txt          # Reference French corpus (Victor Hugo, Les Misérables excerpt)
│   ├── clair.txt              # Plaintext used to build test ciphertexts (Wikipedia "Soupe")
│   ├── chiffre.txt            # Generated substitution ciphertext
│   ├── chiffre_positions.txt  # Generated permutation ciphertext
│   └── schema.txt             # Mermaid flowchart of the MCMC algorithm
├── explication_mcmc.txt       # Plain-language explanation of the MCMC attack
└── rendu.txt                  # Deliverables / deadlines
```

---

## Part 1 — Text statistics & Markov chain (`utils/stats.py`, `utils/app.py`)

- `wiki_text(titre, lang, intro_seule)`: downloads a Wikipedia article via the MediaWiki API, uppercases it, keeps only the 27 states `A–Z` + space (`SATES`), pads to even length.
- `statistics(content)`: total length and count per character.
- `digram_stats(content, largeur=2)`: counts **non-overlapping** digrams (step 2).
- `markov_matrix(digram_stats)`: 27×27 row-normalised transition matrix P(next | current).
- `text_generator(matrix, longueur)`: samples a random text from the Markov chain (output looks "French-shaped" but meaningless).
- Conclusion noted in `stats.py` (for "Paris"): the chain is **not irreducible**, aperiodic on its recurrent class, with a single stationary distribution supported on 22 of 27 states.

`stats.py` is a script (runs on "Paris" and prints everything in ASCII). `app.py` is the interactive version.

## Part 2 — Classical ciphers (`chiffrements/`, `substitution/`, `permutation/`)

- **Caesar** (`chiffrement_cesar.py`): `chiffre_cesar(texte, decalage)` / `dechiffre_cesar`. Non-letters untouched, case preserved.
- **Vigenère** (`chiffrement_vigenere.py`):
  - `chiffre_vigenere(texte, cle)`: classic, key advances only on letters.
  - `chiffre_vigenere_positions(texte, cle)`: key advances on **every** character (spaces included).
  - `cle_inverse_vigenere(cle)`: opposite shifts; decryption = encryption with inverse key.
- **Frequency attack** (`attaque_frequentielle.py`):
  - `FREQUENCES_FR`: French letter frequencies (%).
  - `scores_decalages(texte)`: for each shift 0–25, score = Σ observed_freq(c) × FR_freq(c − shift) (correlation).
  - `attaque_frequentielle_colonnes(crypto, periode, flux)`: splits into `periode` columns (on letters for Vigenère, on raw positions for the permutation cipher), breaks each column as a Caesar, returns per-column shift, the recovered key, a reliability score (min gap between best and 2nd-best shift) and the partially decrypted text.
- **`substitution/cryptogramme.py`**: Caesar wrapper — `chiffre_cryptogramme`, `dechiffre_cryptogramme`, `attaque_frequentielle` (best shift + plaintext).
- **`permutation/bloc.py`** — block transposition (part 1.4):
  - Key = permutation `p` of `0..ℓ-1`; `p[i]` = new position of the char at position `i` in each block of ℓ chars.
  - Subject example: `chiffrer("BONJOUR", "3021") == "OJNBURO"`.
  - Last incomplete block: uses the relative order of the first key values (stays reversible).
  - Functions: `definir_cle`, `verifier_cle`, `cle_inverse`, `formater_cle` (`"3021"` or space-separated if ℓ > 10), `chiffrer`, `dechiffrer`.
- **`permutation/cryptogramme.py`** — combined cipher keyed by a word (e.g. `"LEMON"`):
  - Each letter gives a positional Vigenère shift; the alphabetical order of the letters gives the block permutation.
  - Encrypt = positional Vigenère then permutation; decrypt = inverse.
  - Analysis in comments: permutation keeps letter histogram but breaks neighbouring bigrams (Kasiski fails, text unreadable); per-column frequency attack still recovers the shifts (26·L hypotheses), only the column order (L! options) remains unknown.

### Web UI (`python utils/app.py`)
Stdlib `http.server` on `http://127.0.0.1:8765/`, opens the browser automatically. Enter a Wikipedia title + language → shows:
- interactive 27×27 transition-matrix heatmap (hover for P(y|x), counts, most likely next char),
- character frequency and top digram bar charts,
- generated Markov text, source text, ciphertext, decrypted text, attack results (tabs),
- three cipher cards (Caesar, Vigenère, Permutation), each with **1 Encrypt / 2 Decrypt with key / 3 Attack**.

JSON endpoints: `/api/analyse`, `/api/generer`, `/api/cesar`, `/api/vigenere`, `/api/permutation`, `/api/attaque`, `/api/attaque-vigenere`, `/api/attaque-permutation`.

---

## Part 3 — MCMC attack (`mcmc/`)

One generic Metropolis–Hastings engine, two modes that differ only in *decrypt* and *mutate* functions.

### Scoring (`mcmc/utils/score.py`)
- Alphabet: 26 uppercase letters + space. `normaliser()` removes accents (NFD), expands œ/æ, uppercases, replaces everything else by spaces and collapses spaces.
- Subject's formula:
  ```
  S(k) = ∏_{(x,y)} r(x,y)^{f_k(x,y)}
  r(x,y)   = 1 + count of bigram xy in the reference text
  f_k(x,y) = 1 + count of bigram xy in the text decrypted with k
  ```
- Computed in log-space: `log S(k) = Σ (1 + f_k(x,y)) · log r(x,y)` (`score_log`). `score_texte` computes the exact integer product and is used in tests to validate the log version.
- Bigrams here are **overlapping** (`zip(t, t[1:])`).
- `lire_chiffre` keeps raw spaces (a permutation can produce double spaces).

### Engine (`mcmc/main.py` → `marche_mcmc`)
```
k ← initial key ; s ← log S(k)
repeat n_iterations:
    k' ← muter(k)                      (scores cached per key)
    accept if log U < log S(k') − log S(k)   (selection.accepter_log)
    after burn-in: record visits/score of current state
```
Returns `etats` (states visited after burn-in, with visits + score) and `candidats` (all proposed keys with best score + times proposed). Results are merged, ranked by score (or visits), and the **top N keys** (default 5) are printed with log S, visits, times proposed, key, inverse key and the first 100 decrypted chars. **The human picks** the readable one (the score is only an approximation).

### Mode `lettres` (monoalphabetic substitution, part 1.3)
- State: 26-letter decryption key (string). Spaces are not encrypted.
- Initial key: `cle_heuristique` (i-th most frequent cipher letter → i-th most frequent reference letter) or `cle_aleatoire`.
- Mutation `muter_lettres`: swap two random letters (symmetric proposal).

### Mode `positions` (block permutation, part 1.4)
- State: tuple permutation of `0..ℓ-1`, for ℓ from `--longueur-min` (2) to `--longueur-max` (8).
- Initial key: random permutation; optional multiple restarts per ℓ (`--redemarrages`), merged.
- Mutation `muter_positions`: pick block length L ∈ [1, ℓ−1], start i, destination d; remove the sub-block and reinsert at d (`deplacer_bloc`). Symmetric: (i, L, d) is undone by (d, L, i); i = d leaves the key unchanged.
- For each ℓ prints the top keys plus `log S − log(ℓ!)` (penalty for larger key spaces), then a summary table. Rule: **choose the smallest ℓ whose text is readable**.

### Theoretical justifications (comment block at end of `main.py`)
1. S(k) is a smoothed order-1 Markov likelihood of the decrypted text → with a uniform prior, posterior ∝ S(k).
2. Irreducibility (letters): transpositions generate S₂₆.
3. Irreducibility (positions): single-element moves (L = 1) generate S_ℓ.
4. Aperiodicity: self-transitions exist (i = d move, or Metropolis rejection).
5. Symmetric proposal + acceptance min(1, S(k')/S(k)) → detailed balance for π(k) ∝ S(k).
6. Choice of ℓ: larger ℓ can overfit bigrams by chance → show `log S − log(ℓ!)` and rely on human reading.

### CLI
```bash
# 1. Generate a test ciphertext (prints the true encryption & decryption keys)
python3 mcmc/chiffrer.py --mode lettres --graine 1                       # 1500 chars → mcmc/chiffre.txt
python3 mcmc/chiffrer.py --mode positions --longueur-cle 4 --longueur 3000 --graine 1   # → mcmc/chiffre_positions.txt
#   options: --clair, --sortie, --longueur, --longueur-cle, --cle (26 letters or e.g. 3021), --graine

# 2. Attack
python3 mcmc/main.py --mode lettres
python3 mcmc/main.py --mode positions --longueur-max 8
#   options: --reference (default mcmc/reference.txt), --chiffre, --iterations (20000),
#            --propositions (5), --chauffe (burn-in fraction, 0.10), --graine,
#            --initialisation heuristique|aleatoire (lettres only),
#            --longueur-min (2), --longueur-max (8), --redemarrages (1),
#            --classement score|visites

# 3. Tests
python3 mcmc/tests/test_mcmc.py
```

### Tests (`mcmc/tests/test_mcmc.py`, unittest)
- Block permutation: subject example BONJOUR→OJNBURO, inverse key, key validation, random round-trips for ℓ = 2..8, formatting of keys with ℓ > 10.
- Position mutation: always yields a valid permutation; every (i, L, d) move is undone by (d, L, i).
- Letter substitution: round-trip, inverse is an involution, key validation.
- Score: `score_log` equals `log(score_texte)`; `lire_chiffre` keeps double spaces.
- Combined Vigenère+permutation cipher round-trip with key "LEMON".
- MCMC engine: on a toy 2-state chain, counts 90 visits after a burn-in of 10 over 100 iterations.

### Algorithm diagram
`mcmc/schema.txt` is a Mermaid flowchart: read texts → choose mode → (substitution loop: swap 2 letters, accept if U < S(k')/S(k), keep N best) or (permutation loop over ℓ = 2..ℓmax: move a sub-block, same acceptance, keep N best per ℓ) → display and let the user choose.

---

## Page web de démo (`mcmc/web.py`, `mcmc/web/index.html`)

Single-page demo for the oral exam: paste a ciphertext (or drop a `.txt`), pick the mode, run the existing MCMC attack, watch **"le texte qui se répare"** live, then pick the readable key.

```bash
python3 mcmc/web.py                    # opens http://127.0.0.1:8766/
python3 mcmc/web.py --sans-navigateur  # server only (--port to change the port)
python3 mcmc/tests/test_web.py         # tests for the demo
```

- **Stdlib only, works offline** (no CDN, system fonts). Port 8766, so it doesn't clash with `utils/app.py` (8765).
- **No existing file was modified.** `marche_mcmc`, `fusionner_*`, `classer`, the init/mutation/decrypt functions and `score.py` are reused unchanged.
- **Live view without touching the engine:** `marche_mcmc` calls `muter(current_key)` once per iteration. `web.py` wraps the mutation in an `Observateur`, which takes a snapshot every `intervalle_suivi` iterations (iteration, ℓ, log S, first 80 decrypted chars) and raises `Annulation` when the run is cancelled.
- The attack runs in a **thread**. Starting a new attack cancels the previous one, because Python's `random` module is shared. The engine is very fast because scores are cached (20,000 iterations take < 1 s), so the page **replays the snapshots over ~3 s** and then shows the results.
- Positions-mode input keeps every space and maps each character to a single character, so the block alignment is preserved. Substitution-mode input goes through `normaliser()`, which means accented text can be pasted.

| Endpoint | Role |
|---|---|
| `GET /` | the page |
| `POST /api/attaque` | `{texte, mode, iterations, propositions, graine, chauffe, initialisation, classement, longueur_min, longueur_max, redemarrages, intervalle_suivi}` → `{id}` |
| `GET /api/etat?id=…&depuis=n` | `{termine, annule, erreur, iteration, total, longueur_en_cours, instantanes[n:], nb_instantanes, duree, resultats?}`, polled every 300 ms |
| `POST /api/annuler` | `{id}`: stops the run. In positions mode the finished ℓ values are kept. |
| `GET /api/frequences` | letter (%) and space frequencies of `mcmc/reference.txt`, for the "Fréquence des caractères" panel |
| `GET /api/exemple?mode=lettres\|positions` | contents of `mcmc/chiffre.txt` / `mcmc/chiffre_positions.txt` |
| `POST /api/chiffrer` | `{texte, mode, longueur_cle}`: encrypts with a random key (same logic as `chiffrer.py`, no file written). The key is hidden behind "Révéler la clé". |

`resultats` mirrors the CLI output. In substitution mode: the top N with rank, log S, visits, times proposed, key, inverse key and full decrypted text. In permutation mode: the top N **per ℓ** plus a summary table with `log S − log(ℓ!)`.

UI: blue `#2563EB` marks automatic steps and orange `#EA580C` marks human actions. A step banner shows `1 Texte → 2 Mode → 3 Attaque → 4 Choix de la clé`. The page also has a progress bar (with `ℓ = k / max`), a Cancel button, the live panel (changed characters highlighted), a hand-drawn SVG curve of log S (one line per run), proposal cards ("Tout voir", "Choisir cette clé"), ℓ tabs plus the summary table (★ = best penalised score), the final text with "Copier", and errors shown inside the page.

**"Fréquence des caractères" panel (helps choose the mode):** computed live in the browser from the pasted ciphertext.
- Chart: 26 letters, ciphertext vs French reference.
- Measures: top 5 letters (vs French), number of double spaces, number of letters analysed.

## Extra de Mathis — highlighting non-French words (`mcmc/utils/dictionnaire.py`)

Display only. It does **not** touch the attack (score, mutation, acceptance, selection).
- `charger_dictionnaire()` reads `mcmc/dictionnaire_fr.txt` (325,158 words, one per line) through `normaliser()`, once (cached). It returns `None` if the file is missing.
- `analyser_mots(texte, dico)` splits the text into words and returns `{reconnus, total, pourcentage, inconnus: [(start, end), …]}`. `resume_mots()` → `mots reconnus : 64 % (7/11)`.
- **Terminal** (`afficher_propositions` in `main.py`): unknown words are shown in yellow (ANSI) when stdout is a terminal, `[MOT]` otherwise (pipe, `NO_COLOR`). The % line is printed under each proposition and is computed on the full text.
- **Web page:**
  - unknown words highlighted in yellow in the proposals and the final text;
  - "mots reconnus" shown under each proposal;
  - a "mots reconnus" column in the permutation ℓ table.
- On the example: right key ≈ 98–99 % (only `WEB`, `VERIFIABILITE`, `QU`, `SOUP` unknown); wrong keys ≈ 15–23 %.
- Tests: `python3 mcmc/tests/test_dictionnaire.py`.

---

## Known quirks / notes
- `stats.py`/`app.py` count digrams **non-overlapping** (step 2) whereas the MCMC score uses **overlapping** bigrams.
- `stats.py` executes on import (top-level script code) and needs `requests`; `app.py` is stdlib-only.
- Two different "permutation" notions exist: `permutation/bloc.py` (pure transposition, attacked by MCMC) and `permutation/cryptogramme.py` (Vigenère + word-keyed transposition, attacked by per-column frequency analysis in the web UI).
- The MCMC never auto-selects a key: it proposes the top 5 for human validation (described in `explication_mcmc.txt`).
