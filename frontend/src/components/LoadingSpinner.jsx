function LoadingSpinner({ message = 'Loading...' }) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px]">
      <div className="relative">
        <div className="w-16 h-16 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
      </div>
      <p className="mt-4 text-gray-600 font-medium">{message}</p>
    </div>
  );
}

export default LoadingSpinner;
