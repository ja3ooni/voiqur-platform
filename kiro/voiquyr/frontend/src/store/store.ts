import { configureStore } from '@reduxjs/toolkit';
import configurationReducer from './slices/configurationSlice';
import audioStreamReducer from './slices/audioStreamSlice';
import analyticsReducer from './slices/analyticsSlice';

const rootReducer = {
  configuration: configurationReducer,
  audioStream: audioStreamReducer,
  analytics: analyticsReducer,
};

export const store = configureStore({
  reducer: rootReducer,
});

// Infer the `RootState` and `AppDispatch` types from the store itself
export type RootState = ReturnType<typeof store.getState>;
// Inferred type: {posts: PostsState, comments: CommentsState, users: UsersState}
export type AppDispatch = typeof store.dispatch;
