import { Component } from 'react';

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-background flex items-center justify-center p-6">
          <div className="card text-center max-w-sm">
            <img
              src="/images/penguin-group.png"
              alt="펭귄 그룹"
              className="w-32 h-32 object-contain mx-auto mb-4"
            />
            <h2 className="text-xl font-bold mb-2">앗, 문제가 생겼어요!</h2>
            <p className="text-text-secondary mb-4">
              펭귄 친구들이 열심히 고치고 있어요.<br />잠시 후 다시 시도해주세요.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.href = '/';
              }}
              className="btn-primary"
            >
              홈으로 돌아가기
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
