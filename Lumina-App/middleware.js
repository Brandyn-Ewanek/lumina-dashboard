import { next } from '@vercel/edge';

export const config = {
  matcher: '/(.*)',
};

export default function middleware(req) {
  const basicAuth = req.headers.get('authorization');

  if (basicAuth) {
    const authValue = basicAuth.split(' ')[1];
    const [user, pwd] = atob(authValue).split(':');

    if (user === 'user' && pwd === '123') {
      return next(); // Unlocks the dashboard
    }
  }

  // If no password or wrong password, block the page and trigger the native browser pop-up
  return new Response('Authentication Required', {
    status: 401,
    headers: {
      'WWW-Authenticate': 'Basic realm="Lumina Strategies Secure Area"',
    },
  });
}