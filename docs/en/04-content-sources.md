# Content Sources

> Language: [中文](../zh/04-content-sources.md) · [日本語](../ja/04-content-sources.md) · **English**
> Status: Draft v0.1 · Updated: 2026-09-15
> The Chinese version is the source of truth. If versions differ, the Chinese version wins.
> This document lists the external sources used for the brand catalog and magazine learning, and the rules for using them. URLs and terms of use will be verified one by one during M0.

## 1. Assumptions

| Topic | Decision |
|---|---|
| Launch market | Japan |
| Audience | Young adults aged 18–30 |
| Platform | Web |
| Prices & currency | Japanese yen (JPY), taken from brands' Japanese sites |

## 2. Launch brands

We start with well-known brands that have large catalogs to validate mixing the user's wardrobe with brand pieces.

| Brand | Japanese site | Positioning | Main role in looks |
|---|---|---|---|
| UNIQLO | https://www.uniqlo.com/jp/ | Basics | Base layers, basic bottoms, the neutral foundation of a palette |
| ZARA | https://www.zara.com/jp/ | Fast fashion · trends | Current silhouettes and trend pieces |
| H&M | https://www2.hm.com/ja_jp/ | Fast fashion · affordable | Affordable trend pieces, accessories |
| NIKE | https://www.nike.com/jp/ | Sportswear | Sneakers, sport outerwear, sporty looks |
| adidas | https://www.adidas.jp/ | Sportswear · retro | Sneakers, retro sportswear pieces |

**Later candidates** (added as needed after validation): GU, BEAMS, UNITED ARROWS, New Balance, Levi's.

### 2.1 Rules for brand data

- We store only: product name, category, color, material, price, official URL, fetch time, availability, and a thumbnail reference used for tagging.
- Brand product images are not stored long-term on our servers or displayed publicly. Displays link back to the official site.
- Renders that include brand products are labeled as illustrations and link to the official page.
- Respect robots.txt and terms of use, and keep request rates low. Never get around CAPTCHAs or bot protection.
- Confirm usage rights with brands or affiliate channels before commercial launch.

## 3. Magazines & fashion media (first-batch proposal)

### 3.1 Selection criteria

1. Readership is mainly young adults and relevant to Japan (international outlets focus on trends and street culture).
2. Content centers on **styling techniques, how to combine pieces, and street snaps**, not news or celebrity gossip.
3. Articles are available on the web. Print issues are rarely published online in full, so the learning pipeline reads web articles first.
4. Coverage spans menswear and womenswear, and basic, trend and sporty styles, matching the launch brands.

### 3.2 Japanese magazines

| Outlet | Publisher | Readers | What to learn | Priority |
|---|---|---|---|---|
| POPEYE | Magazine House | Men · around 20 | “City boy” style, combining basics, seasonal outfits | P0 |
| MEN'S NON-NO | Shueisha | Men · 20s | Affordable pieces and basics, color, fit and proportion | P0 |
| non-no | Shueisha | Women · 20s | Everyday affordable outfits, re-wearing pieces many ways | P0 |
| ViVi | Kodansha | Women · late teens to 20s | Trend pieces, Korean-inspired and Y2K styles | P0 |
| FUDGE | San-ei | Men & women · 20s | Mixing vintage, layering, accessories | P1 |
| NYLON JAPAN | Caelum | Men & women · 20s | Street and subculture styles | P1 |
| smart | Takarajimasha | Men · 20s | Streetwear, sporty mixes, sneaker outfits | P1 |
| mina | Shufunotomo | Women · 20s | Affordable outfits built on fast fashion | P1 |

### 3.3 Japanese web media

| Outlet | Type | What to learn | Priority |
|---|---|---|---|
| FASHIONSNAP | Street snaps + fashion news | How people actually dress in Tokyo street snaps, trend pieces | P0 |
| WWDJAPAN | Industry media | Seasonal trends and brand moves (trend context only, not a direct source of wears) | P1 |

### 3.4 International media

| Outlet | Type | What to learn | Priority |
|---|---|---|---|
| Highsnobiety | Trends · street culture | Street styling, pairing sneakers and sportswear brands | P0 |
| Vogue Runway | Collection reviews | Seasonal runway trends; source for trend cards | P0 |
| Hypebeast | Trends · sneakers | NIKE / adidas releases and trend pieces | P1 |
| i-D | Youth culture | How young people approach style, emerging looks | P1 |
| Dazed | Youth culture | Experimental wears and subculture styling | P1 |
| GQ (Style) | Menswear | How-to menswear styling and core principles | P1 |
| Who What Wear | Womenswear | How-to womenswear styling and combining pieces | P1 |

**P0 is 7 sources**, the first batch for the M5 learning pipeline. P1 sources are added after P0 is running and source quality has been evaluated.

### 3.5 Chinese-language media (later)

With Japan as the launch market, Chinese-language media stays out of the learning pipeline for now. For terminology and tone for Chinese-speaking users, candidates for later are VOGUE China, GQ China and NOWRE.

## 4. Rules for magazine content

This is the highest copyright risk in the project. Every developer must follow these rules:

1. **Extract abstract techniques only**, for example “three values of one hue, darkening from base to outer layer.” The technique is an idea; we never copy the expression.
2. **Rewrite in our own words.** Technique cards must not contain copied passages. A quote is limited to one sentence, in quotation marks, with its source.
3. **Store no original text or images.** After reading, the pipeline keeps only the technique card and the source (outlet, article title, URL, date).
4. **Access content lawfully.** Read only public web articles or licensed content. The terms of all-you-can-read digital magazine services usually prohibit AI extraction, so check the terms or get a license first.
5. **Human review.** Candidate cards join the live knowledge base only after evals and human review.

## 5. Source quality review

Each quarter, compute these per source to decide whether to keep, deprioritize or replace it:

- Review pass rate of candidate cards
- Number of times its cards are cited in looks
- Save rate of looks that cite its cards
- Duplication rate against existing cards
