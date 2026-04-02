import { useMutation } from "@tanstack/react-query";
import { loginGoogle } from "../api/login-google";
import { loginKakao } from "../api/login-kakao";

export function useKakaoLoginMutation() {
  return useMutation({
    mutationFn: (code: string) => loginKakao(code),
  });
}

export function useGoogleLoginMutation() {
  return useMutation({
    mutationFn: (idToken: string) => loginGoogle(idToken),
  });
}
