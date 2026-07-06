# Launch notes

Copy for sharing Delta Terminal. Before posting: put a **screenshot/GIF at the
top of the README**, and make sure it runs (or at least looks great in the GIF).
Swap `[link]` for the repo URL.

---

## Hacker News

Post the repo link, then add this as your first comment.

**Title**

```
Show HN: Delta Terminal – a markets/data terminal built from free public APIs
```

**First comment**

> I kept reading about how Bloomberg terminals cost like $25k/year, and it bugged
> me because a lot of what they show is just… public data. So I spent a while
> seeing how much of it I could pull together for free.
>
> It ended up being ~48 feeds — stocks, crypto, macro, options flow, SEC filings,
> and then a bunch of random stuff I got curious about like live flights, ships,
> earthquakes, and weather. It's a FastAPI backend that serves everything over
> REST + a websocket, with a panel UI on top (and an Electron app if you want it
> as a desktop thing).
>
> Fair warning, it's held together with free APIs so some feeds rate-limit or
> break and I just have them fail quietly instead of taking the whole thing down.
> Definitely a personal project, not something serious.
>
> Repo's here: [link]. Would genuinely love feedback, or ideas for feeds to add.

---

## Reddit (r/Python, r/selfhosted)

**Title**

```
I got annoyed that Bloomberg terminals cost $25k so I built a free one from public APIs
```

**Body**

> Most of what those expensive terminals show is public data, so I wanted to see
> how far I could get pulling it together myself.
>
> Turned into ~48 live feeds — stocks, crypto, macro, options flow, SEC filings,
> plus random stuff I got nerd-sniped by (live planes, ships, earthquakes,
> weather). Backend's FastAPI serving REST + a websocket, front end is a panel UI,
> and there's an Electron desktop build too.
>
> [gif here]
>
> It's free and MIT licensed: [link]
>
> Heads up it's a side project and the free APIs are flaky, so expect a feed to
> occasionally be down. Curious what you'd want it to show — happy to add feeds.

For **r/selfhosted**, open with: "I wanted a data terminal I could self-host for
free instead of paying a vendor, so I built one."

---

## X / Twitter

> bloomberg terminals cost ~$25k/yr and most of what they show is just public
> data, so i built a free one
>
> ~48 live feeds — stocks, crypto, macro, options flow, SEC filings, + random
> stuff like live planes/ships/earthquakes. fastapi + websocket backend, panel
> UI, electron app
>
> free + open source: [link] [gif]

---

## Tips

- Post **Tue–Thu morning US Eastern** — HN and Reddit are most active then.
- **Reply to every comment for the first few hours.** Engagement drives ranking.
- Lead with the feeling (**"$25k annoyed me"**), not a feature list.
- Optional but effective: mention **"I'm in high school and this was my summer
  project."** People root for that, and it explains any rough edges.
- Keep replies casual: "yeah that feed's janky lol, it's on my list" beats a
  formal answer.
- Don't oversell. Humble + honest outperforms hype on these sites.
