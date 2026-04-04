export type AuthUserDto = {
  id: number;
  nickname: string;
  email: string;
  is_new_user?: boolean;
};

export type LoginResponseDto = {
  access_token: string;
  refresh_token: string;
  user: AuthUserDto;
};

export type RefreshTokenResponseDto = {
  access_token: string;
};

export type MeResponseDto = {
  id: number;
  nickname: string;
  email: string;
};
