import { useState } from "react";
import { Button } from "../../../shared/components/ui/button";
import { ExpiresIn } from "../api/create-share-link";
import { useCreateShareLinkMutation } from "../hooks/use-create-share-link-mutation";

type ShareLinkModalProps = {
  tripId: string;
};

const expiresInOptions: { value: ExpiresIn; label: string }[] = [
  { value: "1d", label: "1일" },
  { value: "7d", label: "7일" },
  { value: "unlimited", label: "무제한" },
];

export function ShareLinkModal({ tripId }: ShareLinkModalProps) {
  const [expiresIn, setExpiresIn] = useState<ExpiresIn>("7d");
  const [shareUrl, setShareUrl] = useState("");
  const [copyMessage, setCopyMessage] = useState("");
  const createShareLinkMutation = useCreateShareLinkMutation(tripId);

  const handleCreateLink = async () => {
    setCopyMessage("");
    try {
      const result = await createShareLinkMutation.mutateAsync({ expires_in: expiresIn });
      setShareUrl(result.share_url);
    } catch {
      // createShareLinkMutation.isError below already surfaces this.
    }
  };

  const handleCopy = async () => {
    if (!shareUrl) {
      return;
    }

    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopyMessage("링크를 복사했어요.");
    } catch {
      setCopyMessage("복사에 실패했어요. 링크를 직접 선택해서 복사해 주세요.");
    }
  };

  return (
    <div className="card">
      <h2 className="section-title">공유 링크 만들기</h2>
      <div className="stack">
        <div className="field">
          <span>권한</span>
          <p className="section-subtitle" style={{ margin: 0 }}>
            읽기 전용 (편집 가능 링크는 아직 지원하지 않아요)
          </p>
        </div>
        <label className="field">
          <span>만료 기간</span>
          <select
            onChange={(event) => setExpiresIn(event.target.value as ExpiresIn)}
            value={expiresIn}
          >
            {expiresInOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        {shareUrl ? (
          <label className="field">
            <span>생성된 링크</span>
            <input readOnly value={shareUrl} />
          </label>
        ) : null}

        {createShareLinkMutation.isError ? (
          <p className="planner-feedback error">링크를 생성하지 못했습니다. 잠시 후 다시 시도해 주세요.</p>
        ) : null}
        {copyMessage ? <p className="planner-feedback success">{copyMessage}</p> : null}

        <div className="row">
          <Button disabled={createShareLinkMutation.isPending} onClick={handleCreateLink} type="button">
            {createShareLinkMutation.isPending ? "생성 중..." : "링크 생성"}
          </Button>
          <Button disabled={!shareUrl} onClick={handleCopy} type="button" variant="secondary">
            URL 복사
          </Button>
        </div>
      </div>
    </div>
  );
}
