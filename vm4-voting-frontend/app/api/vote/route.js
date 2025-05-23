export async function POST(request) {
  try {
    const data = await request.json();
    console.log("투표 데이터 받음:", data);
    return new Response(JSON.stringify({ success: true }), {
      status: 200,
      headers: { "Content-Type": "application/json" }
    });
  } catch (error) {
    console.error("투표 처리 중 오류:", error);
    return new Response(JSON.stringify({ success: false, error: error.message }), {
      status: 500,
      headers: { "Content-Type": "application/json" }
    });
  }
}

export async function GET() {
  const results = {
    monthly: { for: 10, against: 5 },
    biweekly: { for: 8, against: 7 }
  };
  
  return new Response(JSON.stringify(results), {
    status: 200,
    headers: { "Content-Type": "application/json" }
  });
}
