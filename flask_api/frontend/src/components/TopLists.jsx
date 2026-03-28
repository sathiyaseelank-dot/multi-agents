import { useAnalyticsStore } from '../stores/analyticsStore';
import { LoadingSpinner } from './LoadingSpinner';
import { EmptyState } from './EmptyState';

export function TopLists({ topUsers, topConversations }) {
  const { isLoading } = useAnalyticsStore();

  const formatDate = (dateString) => {
    if (!dateString) return '-';
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <section className="top-lists">
      <div className="top-list-card">
        <h2>Top Active Users</h2>
        <div className="table-container">
          {isLoading.topUsers ? (
            <div className="loading-cell"><LoadingSpinner /></div>
          ) : topUsers.length === 0 ? (
            <EmptyState message="No user data available" />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Email</th>
                  <th>Messages</th>
                  <th>Last Activity</th>
                </tr>
              </thead>
              <tbody>
                {topUsers.map((user) => (
                  <tr key={user.id}>
                    <td>{user.username}</td>
                    <td>{user.email}</td>
                    <td>{user.message_count}</td>
                    <td>{formatDate(user.last_activity)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <div className="top-list-card">
        <h2>Top Conversations</h2>
        <div className="table-container">
          {isLoading.topConversations ? (
            <div className="loading-cell"><LoadingSpinner /></div>
          ) : topConversations.length === 0 ? (
            <EmptyState message="No conversation data available" />
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Type</th>
                  <th>Participants</th>
                  <th>Messages</th>
                </tr>
              </thead>
              <tbody>
                {topConversations.map((conv) => (
                  <tr key={conv.id}>
                    <td>{conv.name || 'Unnamed'}</td>
                    <td>{conv.is_group ? 'Group' : 'Direct'}</td>
                    <td>{conv.participant_count}</td>
                    <td>{conv.message_count}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </section>
  );
}
