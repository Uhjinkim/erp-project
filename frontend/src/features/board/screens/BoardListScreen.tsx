import { useCallback, useEffect, useMemo, useRef, useState } from "react"

import { listPosts } from "../../../api/board"
import { Badge, Button, Card, EmptyState, ErrorState, Select, Spinner, Table, TextInput } from "../../../components/ui"
import type { Post } from "../../../types/board"
import styles from "../board.module.css"
import { filterPosts, formatDateTime, noticeCategoryLabels, postHref, writeHref, writerLabel } from "../boardModel"
import type { SearchField } from "../boardModel"

export function BoardListScreen({ enabled }: { enabled: boolean }) {
  const [posts, setPosts] = useState<Post[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [field, setField] = useState<SearchField>("title")
  const [query, setQuery] = useState("")
  const generation = useRef(0)

  const load = useCallback(async () => {
    if (!enabled) return
    const run = ++generation.current
    setLoading(true)
    setError("")
    try {
      const postData = await listPosts()
      if (run !== generation.current) return
      setPosts(postData)
    } catch (caught) {
      if (run === generation.current) setError(caught instanceof Error ? caught.message : "게시글을 불러오지 못했습니다.")
    } finally {
      if (run === generation.current) setLoading(false)
    }
  }, [enabled])

  useEffect(() => {
    const counter = generation
    if (!enabled) return
    const timer = window.setTimeout(() => void load(), 0)
    return () => { counter.current++; window.clearTimeout(timer) }
  }, [enabled, load])

  const visible = useMemo(() => filterPosts(posts, field, query), [posts, field, query])

  const actions = <div className={styles.row}>
    <a className={styles.titleLink} href={writeHref}>게시글 작성</a>
    <Button variant="ghost" size="small" disabled={loading || !enabled} onClick={() => void load()}>새로고침</Button>
  </div>

  if (!enabled) return <EmptyState title="서버 연결 후 게시글을 불러옵니다" />
  if (error) return <ErrorState onRetry={() => void load()}>{error}</ErrorState>

  return <Card title="게시글 목록" actions={actions}>
    <div className={styles.stack}>
      <div className={styles.filters}>
        <Select label="검색 대상" value={field} onChange={(event) => setField(event.target.value as SearchField)}>
          <option value="title">제목</option>
          <option value="writer">작성자</option>
        </Select>
        <TextInput label="검색어" type="search" placeholder={field === "title" ? "제목으로 검색" : "작성자로 검색"} value={query} onChange={(event) => setQuery(event.target.value)} />
      </div>
      {loading && <Spinner label="게시글을 불러오는 중" />}
      {!loading && posts.length === 0 && <EmptyState title="아직 게시글이 없습니다">게시글 작성으로 첫 글을 남길 수 있습니다.</EmptyState>}
      {!loading && posts.length > 0 && visible.length === 0 && <EmptyState title="검색 결과가 없습니다">검색어를 바꾸거나 지워 보세요.</EmptyState>}
      {!loading && visible.length > 0 && <Table caption={`게시글 ${visible.length}건`}>
        <thead>
          <tr><th scope="col">구분</th><th scope="col">제목</th><th scope="col">작성자</th><th scope="col">작성일</th></tr>
        </thead>
        <tbody>
          {visible.map((post) => <tr key={post.post_id}>
            <td><div className={styles.row}>
              <Badge tone={post.post_type === "공지" ? "info" : "neutral"}>{post.post_type}</Badge>
              {post.notice_category && <span className={styles.muted}>{noticeCategoryLabels[post.notice_category]}</span>}
            </div></td>
            <td>
              <a className={styles.titleLink} href={postHref(post.post_id)}>{post.title}</a>
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
