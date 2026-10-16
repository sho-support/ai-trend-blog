    ]

    print(
        "取得本文文字数:",
        len(source_text),
    )

    article_html = generate_article(
        candidate,
        source_text,
    )

    title = extract_title(
        article_html
    )

    description = extract_description(
        article_html,
        title,
    )

    now = datetime.now(JST)

    filename = (
        now.strftime("%Y-%m-%d_%H%M%S")
        + ".html"
    )

    ARTICLE_DIR.mkdir(
        exist_ok=True
    )

    filepath = ARTICLE_DIR / filename

    page_html = build_page(
        title=title,
        description=description,
        article_html=article_html,
        candidate=candidate,
        filename=filename,
        now=now,
    )

    filepath.write_text(
        page_html,
        encoding="utf-8",
    )

    update_index(
        title,
        filename,
        candidate,
    )

    history.append(
        {
            "title": title,
            "source_title": candidate["title"],
            "page_title": candidate.get(
                "page_title",
                candidate["title"],
            ),
            "source_name": candidate["source_name"],
            "url": candidate["url"],
            "filename": filename,
            "created_at": now.isoformat(),
        }
    )

    history = history[-1000:]
    save_history(history)

    # indexを更新した後、トップページSEOも最終更新。
    ensure_existing_seo_tags(history)

    generate_sitemap(history)
    generate_robots()

    print("")
    print("========================")
    print("記事生成成功")
    print("========================")
    print("記事タイトル:", title)
    print("保存先:", filepath)
    print("情報源:", candidate["url"])
    print(
        "実ページタイトル:",
        candidate.get(
            "page_title",
            candidate["title"],
        ),
    )
    print("GA4:", GA_MEASUREMENT_ID)
    print(
        "Sitemap Index:",
        SITEMAP_INDEX_FILE,
    )
    print(
        "Site Sitemap:",
        SITE_SITEMAP_FILE,
    )
    print(
        "Articles Sitemap:",
        ARTICLES_SITEMAP_FILE,
    )
    print(
        "Legacy Sitemap:",
        SITEMAP_FILE,
    )
    print("Robots:", ROBOTS_FILE)
    print(
        "Canonical:",
        f"{SITE_BASE_URL}/articles/{filename}",
    )
    print("========================")


if __name__ == "__main__":
    main()
