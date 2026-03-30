'use client'

import { useState, useEffect } from 'react'
import Header from '@/components/Header'

interface LinkedInPost {
  id: string
  content: string
  scheduled_time?: string
  status: 'draft' | 'scheduled' | 'posted' | 'failed'
  engagement?: {
    likes: number
    comments: number
    shares: number
  }
  created_at: string
}

interface LinkedInStats {
  profile_views: number
  post_impressions: number
  connection_requests: number
  messages_unread: number
}

export default function LinkedInPage() {
  const [stats, setStats] = useState<LinkedInStats>({
    profile_views: 0,
    post_impressions: 0,
    connection_requests: 0,
    messages_unread: 0
  })
  const [posts, setPosts] = useState<LinkedInPost[]>([])
  const [loading, setLoading] = useState(true)
  const [showCompose, setShowCompose] = useState(false)
  const [newPostContent, setNewPostContent] = useState('')
  const [scheduleTime, setScheduleTime] = useState('')

  useEffect(() => {
    // Fetch LinkedIn stats
    fetch('/api/linkedin/stats')
      .then(r => r.json())
      .then(data => setStats(data))
      .catch(() => {})
      .finally(() => setLoading(false))

    // Fetch posts
    fetch('/api/linkedin/posts')
      .then(r => r.json())
      .then(data => setPosts(data.posts || []))
      .catch(() => {})
  }, [])

  const handleCreatePost = async () => {
    if (!newPostContent.trim()) return
    
    try {
      const endpoint = scheduleTime ? '/api/linkedin/schedule' : '/api/linkedin/post'
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: newPostContent,
          scheduled_time: scheduleTime || undefined
        }),
      })
      
      if (res.ok) {
        alert(scheduleTime ? '✅ Post scheduled!' : '✅ Post published!')
        setNewPostContent('')
        setScheduleTime('')
        setShowCompose(false)
        // Refresh posts
        fetch('/api/linkedin/posts')
          .then(r => r.json())
          .then(data => setPosts(data.posts || []))
      } else {
        const data = await res.json()
        alert(`❌ Error: ${data.error}`)
      }
    } catch (err) {
      alert('❌ Failed to create post')
    }
  }

  const handleDeletePost = async (postId: string) => {
    if (!confirm('Delete this post?')) return
    
    try {
      const res = await fetch(`/api/linkedin/posts/${postId}`, { method: 'DELETE' })
      if (res.ok) {
        setPosts(posts.filter(p => p.id !== postId))
        alert('✅ Post deleted')
      }
    } catch {
      alert('❌ Failed to delete')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <Header 
        title="💼 LinkedIn Manager" 
        subtitle="Professional Network Automation • Silver Tier"
      />

      <main className="p-6 space-y-6">
        
        {/* Stats Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="bg-gradient-to-br from-blue-950/50 to-blue-900/30 rounded-xl p-6 border border-blue-800/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-blue-400">{stats.profile_views}</div>
                <div className="text-sm text-slate-400 mt-1">👁️ Profile Views</div>
              </div>
              <div className="text-4xl">👤</div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-purple-950/50 to-purple-900/30 rounded-xl p-6 border border-purple-800/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-purple-400">{stats.post_impressions}</div>
                <div className="text-sm text-slate-400 mt-1">📊 Post Impressions</div>
              </div>
              <div className="text-4xl">📈</div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-green-950/50 to-green-900/30 rounded-xl p-6 border border-green-800/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-green-400">{stats.connection_requests}</div>
                <div className="text-sm text-slate-400 mt-1">🤝 Connection Requests</div>
              </div>
              <div className="text-4xl">➕</div>
            </div>
          </div>

          <div className="bg-gradient-to-br from-amber-950/50 to-amber-900/30 rounded-xl p-6 border border-amber-800/30">
            <div className="flex items-center justify-between">
              <div>
                <div className="text-3xl font-bold text-amber-400">{stats.messages_unread}</div>
                <div className="text-sm text-slate-400 mt-1">💬 Unread Messages</div>
              </div>
              <div className="text-4xl">✉️</div>
            </div>
          </div>
        </section>

        {/* Quick Actions */}
        <section className="flex gap-4">
          <button 
            onClick={() => setShowCompose(true)}
            className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white font-semibold py-4 px-6 rounded-xl transition-all flex items-center justify-center gap-3"
          >
            <span className="text-2xl">✍️</span>
            <span>Create Post</span>
          </button>
          <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-4 px-6 rounded-xl transition-all flex items-center justify-center gap-3">
            <span className="text-2xl">🔍</span>
            <span>Find Leads</span>
          </button>
          <button className="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold py-4 px-6 rounded-xl transition-all flex items-center justify-center gap-3">
            <span className="text-2xl">⚙️</span>
            <span>Settings</span>
          </button>
        </section>

        {/* Compose Modal */}
        {showCompose && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur flex items-center justify-center z-50 p-4">
            <div className="bg-slate-900 rounded-2xl border border-slate-800 w-full max-w-2xl p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-xl font-bold">Create LinkedIn Post</h2>
                <button 
                  onClick={() => setShowCompose(false)}
                  className="text-slate-400 hover:text-slate-200 text-2xl"
                >
                  ×
                </button>
              </div>

              <textarea
                value={newPostContent}
                onChange={(e) => setNewPostContent(e.target.value)}
                placeholder="What do you want to share on LinkedIn?"
                className="w-full h-40 bg-slate-800 border border-slate-700 rounded-xl p-4 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
              />

              <div className="mt-4">
                <label className="block text-sm text-slate-400 mb-2">
                  Schedule for later (optional)
                </label>
                <input
                  type="datetime-local"
                  value={scheduleTime}
                  onChange={(e) => setScheduleTime(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-xl p-3 text-slate-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex gap-3 mt-6">
                <button
                  onClick={handleCreatePost}
                  className="flex-1 bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 text-white font-semibold py-3 px-6 rounded-xl transition-all"
                >
                  {scheduleTime ? '📅 Schedule Post' : '🚀 Publish Now'}
                </button>
                <button
                  onClick={() => setShowCompose(false)}
                  className="px-6 py-3 text-slate-400 hover:text-slate-200 font-semibold"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Posts Grid */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-slate-300">📝 Your Posts</h2>
            <div className="flex gap-2">
              <button className="text-sm text-blue-400 hover:text-blue-300">All Posts</button>
              <span className="text-slate-600">|</span>
              <button className="text-sm text-slate-400 hover:text-slate-300">Scheduled</button>
              <span className="text-slate-600">|</span>
              <button className="text-sm text-slate-400 hover:text-slate-300">Published</button>
            </div>
          </div>

          {loading ? (
            <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-8 text-center">
              <div key="spinner" className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto" />
              <p className="text-slate-400 mt-4">Loading posts...</p>
            </div>
          ) : posts.length === 0 ? (
            <div className="bg-slate-900/60 rounded-xl border border-slate-800 p-8 text-center">
              <div className="text-6xl mb-4">📝</div>
              <h3 className="text-lg font-semibold text-slate-300">No posts yet</h3>
              <p className="text-slate-500 mt-2">Create your first LinkedIn post to get started</p>
              <button 
                onClick={() => setShowCompose(true)}
                className="mt-4 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 px-6 rounded-lg transition"
              >
                Create Post
              </button>
            </div>
          ) : (
            <div className="grid gap-4">
              {posts.map((post) => (
                <div 
                  key={post.id}
                  className="bg-slate-900/60 rounded-xl border border-slate-800 p-6 hover:border-blue-800/50 transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-3 mb-3">
                        <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                          post.status === 'posted' ? 'bg-green-950 text-green-400' :
                          post.status === 'scheduled' ? 'bg-blue-950 text-blue-400' :
                          post.status === 'draft' ? 'bg-slate-800 text-slate-400' :
                          'bg-red-950 text-red-400'
                        }`}>
                          {post.status === 'posted' ? '✅ Published' :
                           post.status === 'scheduled' ? '📅 Scheduled' :
                           post.status === 'draft' ? '📝 Draft' : '❌ Failed'}
                        </span>
                        {post.scheduled_time && (
                          <span className="text-xs text-slate-500">
                            📆 {new Date(post.scheduled_time).toLocaleString()}
                          </span>
                        )}
                      </div>
                      <p className="text-slate-200 whitespace-pre-wrap">{post.content}</p>
                      {post.engagement && (
                        <div className="flex gap-4 mt-4 text-sm text-slate-400">
                          <span>👍 {post.engagement.likes} likes</span>
                          <span>💬 {post.engagement.comments} comments</span>
                          <span>🔄 {post.engagement.shares} shares</span>
                        </div>
                      )}
                    </div>
                    <button 
                      onClick={() => handleDeletePost(post.id)}
                      className="text-slate-500 hover:text-red-400 transition ml-4"
                    >
                      🗑️
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* Features */}
        <section className="bg-gradient-to-br from-blue-950/30 via-purple-950/30 to-pink-950/30 rounded-2xl border border-blue-800/30 p-6">
          <h2 className="text-lg font-semibold text-slate-300 mb-4">💼 LinkedIn Automation Features</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-2xl mb-2">📝</div>
              <h3 className="font-semibold text-slate-200">Post Scheduling</h3>
              <p className="text-sm text-slate-400 mt-1">Schedule posts for optimal engagement times</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-2xl mb-2">📊</div>
              <h3 className="font-semibold text-slate-200">Analytics</h3>
              <p className="text-sm text-slate-400 mt-1">Track impressions, views, and engagement</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-2xl mb-2">🤝</div>
              <h3 className="font-semibold text-slate-200">Auto Connect</h3>
              <p className="text-sm text-slate-400 mt-1">Automated connection requests</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-2xl mb-2">💬</div>
              <h3 className="font-semibold text-slate-200">Message Replies</h3>
              <p className="text-sm text-slate-400 mt-1">Auto-reply to incoming messages</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-2xl mb-2">🔍</div>
              <h3 className="font-semibold text-slate-200">Lead Generation</h3>
              <p className="text-sm text-slate-400 mt-1">Find and engage with prospects</p>
            </div>
            <div className="bg-slate-800/50 rounded-lg p-4">
              <div className="text-2xl mb-2">📈</div>
              <h3 className="font-semibold text-slate-200">Content Ideas</h3>
              <p className="text-sm text-slate-400 mt-1">AI-generated post suggestions</p>
            </div>
          </div>
        </section>

      </main>
    </div>
  )
}
