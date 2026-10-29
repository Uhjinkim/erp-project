import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { getEligibleNoticeCategories, listPosts } from "../../../api/board"
import { Button, Card, EmptyState, ErrorState, Select, Spinner, Table, TextInput } from "../../../components/ui"
import type { NoticeCategory, Post } from "../../../types/board"
import styles from "../board.module.css"
import {
  boardNumbers, filterGeneralPosts, filterNoticePosts, formatDateTime, kindOf, noticeCategoryLabels, postHref, writeHref,
  writerLabel,
} from "../boardModel"
import type { BoardKind, CategoryFilter, SearchField } from "../boardModel"

const boardTitles: Record<BoardKind, string> = { notice: "공지게시판", general: "일반게시판" }

export function BoardListScreen({ kind, enabled }: { kind: BoardKind; enabled: boolean }) {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [field, setField] = useState<SearchField>("title")
  const [category, setCategory] = useState<CategoryFilter>("all")
  const [query, setQuery] = useState("")
  const [canWriteNotice, setCanWriteNotice] = useState(false)
  const generation = useRef(0)

  const load = useCallback(async () => {
    if (!enabled) return
    const run = ++generation.current
    setLoading(true)
    setError("")
    try {
      // Notice writing is guidance only; the backend still enforces category permissions.
      const [postData, eligible] = await Promise.all([
        listPosts(),
        kind === "notice" ? getEligibleNoticeCategories().catch(() => []) : Promise.resolve([]),
      ])
      if (run !== generation.current) return
      setPosts(postData)
      setCanWriteNotice(eligible.length > 0)
    } catch (caught) {
      if (run === generation.current) setError(caught instanceof Error ? caught.message : "게시글을 불러오지 못했습니다.")
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [enabled, kind])

  useEffect(() => {
    const counter = generation
    if (!enabled) return
    const timer = window.setTimeout(() => void load(), 0)
    return () => { counter.current++; window.clearTimeout(timer) }
  }, [enabled, load])

  const boardPosts = useMemo(() => posts.filter((post) => kindOf(post) === kind), [posts, kind])
  const numbers = useMemo(() => boardNumbers(posts, kind), [posts, kind])
  const visible = useMemo(
    () => kind === "notice" ? filterNoticePosts(posts, category, query) : filterGeneralPosts(posts, field, query),
    [posts, kind, category, field, query],
  )

  const actions = <div className={styles.row}>
    {(kind === "general" || canWriteNotice) && <a className={styles.titleLink} href={writeHref}>게시글 작성</a>}
    <Button variant="ghost" size="small" disabled={loading || !enabled} onClick={() => void load()}>새로고침</Button>
  </div>

  if (!enabled) return <EmptyState title="서버 연결 후 게시글을 불러옵니다" />
  if (error) return <ErrorState onRetry={() => void load()}>{error}</ErrorState>

  const isNotice = kind === "notice"
  return <Card title={boardTitles[kind]} actions={actions}>
    <div className={styles.stack}>
      <div className={styles.filters}>
        {isNotice
          ? <Select label="공지 분류" value={category} onChange={(event) => setCategory(event.target.value as CategoryFilter)}>
            <option value="all">전체</option>
            {(Object.keys(noticeCategoryLabels) as NoticeCategory[]).map((code) => <option key={code} value={code}>{noticeCategoryLabels[code]}</option>)}
          </Select>
          : <Select label="검색 대상" value={field} onChange={(event) => setField(event.target.value as SearchField)}>
            <option value="title">제목</option>
            <option value="writer">작성자</option>
          </Select>}
        <TextInput label="검색어" type="search" placeholder={isNotice || field === "title" ? "제목으로 검색" : "작성자로 검색"} value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      {loading && <Spinner label="게시글을 불러오는 중" />}
      {!loading && boardPosts.length === 0 && <EmptyState title={isNotice ? "아직 공지가 없습니다" : "아직 게시글이 없습니다"}>
        {isNotice ? "공지 작성 권한이 있는 담당자가 게시글 작성에서 공지를 올릴 수 있습니다." : "게시글 작성으로 첫 글을 남길 수 있습니다."}
      </EmptyState>}
      {!loading && boardPosts.length > 0 && visible.length === 0 && <EmptyState title="검색 결과가 없습니다">분류나 검색어를 바꿔 보세요.</EmptyState>}
      {!loading && visible.length > 0 && <Table caption={`${boardTitles[kind]} ${visible.length}건`}>
        <thead>
          <tr>
            <th scope="col">번호</th>
            {isNotice && <th scope="col">분류</th>}
            <th scope="col">제목</th>
            <th scope="col">작성자</th>
            <th scope="col">작성일</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((post) => <tr key={post.post_id}>
            <td>{numbers.get(post.post_id)}</td>
            {isNotice && <td>{post.notice_category ? noticeCategoryLabels[post.notice_category] : "-"}</td>}
            <td>
              <a className={styles.titleLink} href={postHref(kind, post.post_id)}>{post.title}</a>
              {post.comment_count > 0 && <span className={styles.commentCount} aria-label={`댓글 ${post.comment_count}개`}>댓글 {post.comment_count}</span>}
            </td>
            <td>{writerLabel(post)}</td>
            <td>{formatDateTime(post.created_at)}</td>
          </tr>)}
        </tbody>
      </Table>}
    </div>
  </Card>
}
