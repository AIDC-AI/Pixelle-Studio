export interface User {
  uid: number;
  username: string;
  email: string;
  password: string;
  createdAt: string;
  updatedAt: string;
}

export interface UserResponse extends Omit<User, 'password'> {
  // Password is excluded when returned to the frontend
}

export interface Token {
    access_token: string
    token_type: string
}

export interface CreateUserRequest {
  username: string;
  email: string;
  password: string;
}

export interface UpdateUserRequest {
  username?: string;
  email?: string;
  password?: string;
}
