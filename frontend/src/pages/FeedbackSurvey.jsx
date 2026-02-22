/**
 * FeedbackSurvey.jsx - 전용 피드백 설문 페이지
 * Google Forms 스타일: 1~5점 체크 + 자유의견 + 스크린샷 첨부
 */
import { useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { feedbackApi } from '../api/feedback';
import AppHeader from '../components/layout/AppHeader';

const RATING_CATEGORIES = [
  { key: 'ui_rating', label: 'UI/디자인', description: '화면 구성과 디자인이 사용하기 편한가요?' },
  { key: 'feature_rating', label: '기능 편의성', description: '원하는 기능을 쉽게 찾고 사용할 수 있나요?' },
  { key: 'content_rating', label: '학습 콘텐츠', description: '제공되는 콘텐츠가 유익하고 이해하기 쉬운가요?' },
  { key: 'speed_rating', label: '속도/안정성', description: '앱이 빠르고 안정적으로 작동하나요?' },
  { key: 'overall_rating', label: '전체 만족도', description: '서비스에 전반적으로 만족하시나요?' },
];

export default function FeedbackSurvey() {
  const navigate = useNavigate();
  const fileInputRef = useRef(null);
  const [ratings, setRatings] = useState({});
  const [comment, setComment] = useState('');
  const [screenshotFile, setScreenshotFile] = useState(null);
  const [screenshotPreview, setScreenshotPreview] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState('');

  const allRated = RATING_CATEGORIES.every((cat) => ratings[cat.key]);

  const handleRating = (key, value) => {
    setRatings((prev) => ({ ...prev, [key]: value }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      setError('파일 크기는 5MB 이하만 가능합니다');
      return;
    }

    if (!file.type.startsWith('image/')) {
      setError('이미지 파일만 첨부할 수 있습니다');
      return;
    }

    setError('');
    setScreenshotFile(file);
    const reader = new FileReader();
    reader.onload = (ev) => setScreenshotPreview(ev.target.result);
    reader.readAsDataURL(file);
  };

  const removeScreenshot = () => {
    setScreenshotFile(null);
    setScreenshotPreview(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSubmit = async () => {
    if (!allRated || isSubmitting) return;
    setIsSubmitting(true);
    setError('');

    try {
      let screenshotUrl = null;

      // 스크린샷 업로드 (있으면)
      if (screenshotFile) {
        try {
          const uploadResult = await feedbackApi.uploadScreenshot(screenshotFile);
          screenshotUrl = uploadResult.url;
        } catch {
          // 스크린샷 업로드 실패는 설문 전송을 막지 않음
        }
      }

      await feedbackApi.submitSurvey({
        ...ratings,
        comment: comment || null,
        screenshot_url: screenshotUrl,
      });

      setSubmitted(true);
      setTimeout(() => navigate('/profile'), 2000);
    } catch {
      setError('설문 전송에 실패했습니다. 잠시 후 다시 시도해주세요.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-background pb-24">
        <AppHeader />
        <main className="container py-12 text-center">
          <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }}>
            <img src="/images/penguin-3d.png" alt="Adelie" className="w-16 h-16 mx-auto mb-4" />
            <h2 className="text-xl font-bold mb-2">감사합니다!</h2>
            <p className="text-sm text-text-secondary">소중한 의견이 서비스 개선에 반영됩니다</p>
          </motion.div>
        </main>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background pb-24">
      <AppHeader />
      <main className="container py-6 space-y-6">
        {/* 헤더 */}
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
          <h1 className="text-xl font-bold">아델리에 서비스 평가</h1>
          <p className="text-sm text-text-secondary mt-1">
            각 항목에 대해 1~5점으로 평가해주세요
          </p>
        </motion.div>

        {/* 평가 항목들 */}
        {RATING_CATEGORIES.map((cat, idx) => (
          <motion.div
            key={cat.key}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
            className="card"
          >
            <h3 className="font-bold text-sm mb-1">{cat.label}</h3>
            <p className="text-xs text-text-secondary mb-3">{cat.description}</p>
            <div className="flex gap-2">
              {[1, 2, 3, 4, 5].map((score) => (
                <button
                  key={score}
                  type="button"
                  onClick={() => handleRating(cat.key, score)}
                  className={`flex-1 h-10 rounded-xl text-sm font-bold transition-colors ${
                    ratings[cat.key] === score
                      ? 'bg-primary text-white'
                      : 'bg-surface border border-border text-text-secondary hover:border-primary/40'
                  }`}
                >
                  {score}
                </button>
              ))}
            </div>
          </motion.div>
        ))}

        {/* 자유 의견 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="card"
        >
          <h3 className="font-bold text-sm mb-1">자유 의견 (선택)</h3>
          <p className="text-xs text-text-secondary mb-3">개선 사항이나 건의할 내용이 있다면 남겨주세요</p>
          <textarea
            id="survey-comment"
            name="comment"
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="의견을 입력해주세요"
            aria-label="자유 의견"
            className="w-full p-3 rounded-xl border border-border bg-surface text-sm resize-none"
            rows={4}
            maxLength={2000}
          />
          <p className="text-right text-xs text-text-muted mt-1">{comment.length}/2000</p>
        </motion.div>

        {/* 스크린샷 첨부 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.35 }}
          className="card"
        >
          <h3 className="font-bold text-sm mb-1">에러 화면 캡처 (선택)</h3>
          <p className="text-xs text-text-secondary mb-3">에러가 발생한 화면의 스크린샷을 첨부해주세요</p>

          {screenshotPreview ? (
            <div className="relative">
              <img
                src={screenshotPreview}
                alt="첨부된 스크린샷"
                className="w-full max-h-48 object-contain rounded-xl border border-border"
              />
              <button
                type="button"
                onClick={removeScreenshot}
                className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center rounded-full bg-black/50 text-white text-xs"
              >
                ✕
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full py-6 rounded-xl border-2 border-dashed border-border text-sm text-text-secondary hover:border-primary/40 transition-colors"
            >
              스크린샷 첨부하기
            </button>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleFileChange}
            className="hidden"
          />
        </motion.div>

        {/* 에러 메시지 */}
        {error && (
          <p className="text-sm text-red-500 text-center">{error}</p>
        )}

        {/* 제출 버튼 */}
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
        >
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!allRated || isSubmitting}
            className="w-full py-3.5 rounded-xl font-semibold text-white bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm"
          >
            {isSubmitting ? '전송 중...' : '제출하기'}
          </button>
          {!allRated && (
            <p className="text-xs text-text-muted text-center mt-2">모든 항목을 평가해주세요</p>
          )}
        </motion.div>
      </main>
    </div>
  );
}
