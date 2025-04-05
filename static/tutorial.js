$(document).ready(function() {
    $('#searchForm').on('submit', function(e) {
        e.preventDefault();
        
        const recipe = $('#recipe').val();
        if (!recipe) return;

        $('#loading').removeClass('hidden');
        $('#results').empty();

        $.ajax({
            url: '/search',
            method: 'POST',
            data: { recipe: recipe },
            success: function(response) {
                $('#loading').addClass('hidden');
                
                if (response.videos.length === 0) {
                    $('#results').html(
                        '<p class="text-center text-gray-600">No tutorials found.</p>'
                    );
                    return;
                }

                response.videos.forEach(function(video) {
                    $('#results').append(`
                        <div class="bg-white rounded-lg shadow-md p-6">
                            <div class="flex gap-4">
                                <img src="${video.thumbnail}" 
                                     alt="${video.title}"
                                     class="w-48 h-27 object-cover rounded">
                                <div>
                                    <h2 class="text-xl font-semibold mb-2">${video.title}</h2>
                                    <p class="text-gray-600 mb-1">Channel: ${video.channel || 'Unknown'}</p>
                                    <p class="text-gray-600 mb-1">Views: ${(video.views || 0).toLocaleString()}</p>
                                    <p class="text-gray-600 mb-3">Likes: ${(video.likes || 0).toLocaleString()}</p>
                                    <a href="${video.url}" 
                                       target="_blank"
                                       class="bg-red-500 text-white px-4 py-2 rounded hover:bg-red-600">
                                        Watch on YouTube
                                    </a>
                                </div>
                            </div>
                        </div>
                    `);
                });
                
            },
            error: function() {
                $('#loading').addClass('hidden');
                $('#results').html(
                    '<p class="text-center text-red-500">An error occurred. Please try again.</p>'
                );
            }
        });
    });
});