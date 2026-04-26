export function StateBlock({ text }: { text: string }) {
  return (
    <div className="flex min-h-52 flex-1 items-center justify-center px-4 text-center text-sm text-stone-600">
      {text}
    </div>
  );
}
