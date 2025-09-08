#Hybrid Search with Sparse and Dense Vectors
In this tutorial, we will continue to explore hybrid search in Qdrant, focusing on both sparse and dense vectors. This time, we will work with a collection related to terraforming_plans, and each data point will have a brief description of its content in the payload.

Step 1: Create a collection with sparse vectors
We'll start by creating a collection named terraforming_plans. This collection will support both dense vectors for semantic similarity and sparse vectors for keyword-based search.

PUT /collections/terraforming_plans
{
    "vectors": {
        "size": 4,  
        "distance": "Cosine"  
    },
    "sparse_vectors": {
        "keywords": { }
    }
}
PUT /collections/terraforming_plans
{
    "vectors": {
        "size": 4,  
        "distance": "Cosine"  
    },
    "sparse_vectors": {
        "keywords": { }
    }
}
Explanation:
vectors: Configures the dense vector space with 4 dimensions, using cosine similarity for distance measurement.
sparse_vectors: Configures the collection to support sparse vectors for keyword-based indexing.
Step 2: Insert data points with descriptions
Now, we'll insert three data points into the terraforming_plans collection, each related to a different celestial body (Mars, Jupiter, and Venus). Each point will have both a dense and sparse vector, along with a description in the payload.

PUT /collections/terraforming_plans/points
{
    "points": [
        {
            "id": 1,  
            "vector": {
                "": [0.02, 0.4, 0.5, 0.9],   // Dense vector
                "keywords": {
                   "indices": [1, 42],    // Sparse for "rocky" and "Mars"
                   "values": [0.22, 0.8]  // Weights for these keywords
                }
            },
            "payload": {
                "description": "Plans about Mars colonization."
            }
        },
        {
            "id": 2,  
            "vector": {
                "": [0.3, 0.1, 0.6, 0.4],   
                "keywords": {
                   "indices": [2, 35],    // Sparse for "gas giant" and "icy"
                   "values": [0.15, 0.65]  // Weights for these keywords
                }
            },
            "payload": {
                "description": "Study on Jupiter gas composition."
            }
        },
        {
            "id": 3,  
            "vector": {
                "": [0.7, 0.5, 0.3, 0.8],   
                "keywords": {
                   "indices": [10, 42],    // Sparse for "Venus" and "rocky"
                   "values": [0.3, 0.5]    // Weights for these keywords
                }
            },
            "payload": {
                "description": "Venus geological terrain analysis."
            }
        }
    ]
}
PUT /collections/terraforming_plans/points
{
    "points": [
        {
            "id": 1,  
            "vector": {
                "": [0.02, 0.4, 0.5, 0.9],   // Dense vector
                "keywords": {
                   "indices": [1, 42],    // Sparse for "rocky" and "Mars"
                   "values": [0.22, 0.8]  // Weights for these keywords
                }
            },
            "payload": {
                "description": "Plans about Mars colonization."
            }
        },
        {
            "id": 2,  
            "vector": {
                "": [0.3, 0.1, 0.6, 0.4],   
                "keywords": {
                   "indices": [2, 35],    // Sparse for "gas giant" and "icy"
                   "values": [0.15, 0.65]  // Weights for these keywords
                }
            },
            "payload": {
                "description": "Study on Jupiter gas composition."
            }
        },
        {
            "id": 3,  
            "vector": {
                "": [0.7, 0.5, 0.3, 0.8],   
                "keywords": {
                   "indices": [10, 42],    // Sparse for "Venus" and "rocky"
                   "values": [0.3, 0.5]    // Weights for these keywords
                }
            },
            "payload": {
                "description": "Venus geological terrain analysis."
            }
        }
    ]
}
Explanation:
Dense vector: Represents the semantic features of the data point in a numerical form.
Sparse vector (keywords): Represents the keyword features, with indices mapped to specific keywords and values representing their relevance.
payload: Provides a short description of the data point's content, making it easier to understand what each vector represents.
Step 3: Perform a hybrid search
Next, perform a hybrid search on the terraforming_plans collection, combining both keyword-based (sparse) and semantic (dense) search using Reciprocal Rank Fusion (RRF).

POST /collections/terraforming_plans/points/query
{
    "prefetch": [
        {
            "query": { 
                "indices": [1, 42],   
                "values": [0.22, 0.8]  
            },
            "using": "keywords",
            "limit": 20
        },
        {
            "query": [0.01, 0.45, 0.67, 0.89],
            "using": "",
            "limit": 20
        }
    ],
    "query": { "fusion": "rrf" },  // Reciprocal rank fusion
    "limit": 10,
    "with_payload": true
}
POST /collections/terraforming_plans/points/query
{
    "prefetch": [
        {
            "query": { 
                "indices": [1, 42],   
                "values": [0.22, 0.8]  
            },
            "using": "keywords",
            "limit": 20
        },
        {
            "query": [0.01, 0.45, 0.67, 0.89],
            "using": "",
            "limit": 20
        }
    ],
    "query": { "fusion": "rrf" },  // Reciprocal rank fusion
    "limit": 10,
    "with_payload": true
}
Explanation:
prefetch: Contains two subqueries:
Keyword-based query: Uses the sparse vector (keywords) to search by keyword relevance.
Dense vector query: Uses the dense vector for semantic similarity search.
fusion: rrf: Combines the results from both queries using Reciprocal Rank Fusion (RRF), giving priority to points ranked highly in both searches.
limit: Limits the number of results to the top 10.
Summary
In this tutorial, we:

Created a Qdrant collection called terraforming_plans that supports hybrid search using both dense and sparse vectors.
Inserted data points with both dense and sparse vectors, as well as descriptions in the payload.
Performed a hybrid search combining keyword relevance and dense vector similarity using Reciprocal Rank Fusion.
This approach allows for effective hybrid search, combining textual and semantic search capabilities, which can be highly useful in applications involving complex search requirements.



#Quickstart: Vector Search for Beginners
Qdrant is designed to find the approximate nearest data points in your dataset. In this quickstart guide, you'll create a simple database to track space colonies and perform a search for the nearest colony based on its vector representation.

Click RUN to send the API request. The response will appear on the right.
You can also edit any code block and rerun the request to see different results.
Step 1: Create a collection
First, we’ll create a collection called star_charts to store the colony data. Each location will be represented by a vector of four dimensions, and we'll use the Dot product as the distance metric for similarity search.

Run this command to create the collection:

PUT collections/star_charts
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
PUT collections/star_charts
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
Step 2: Load data into the collection
Now that the collection is set up, let’s add some data. Each location will have a vector and additional information (payload), such as its name.

Run this request to add the data:

PUT collections/star_charts/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.05, 0.61, 0.76, 0.74],
      "payload": {
        "colony": "Mars"
      }
    },
    {
      "id": 2,
      "vector": [0.19, 0.81, 0.75, 0.11],
      "payload": {
        "colony": "Jupiter"
      }
    },
    {
      "id": 3,
      "vector": [0.36, 0.55, 0.47, 0.94],
      "payload": {
        "colony": "Venus"
      }
    },
    {
      "id": 4,
      "vector": [0.18, 0.01, 0.85, 0.80],
      "payload": {
        "colony": "Moon"
      }
    },
    {
      "id": 5,
      "vector": [0.24, 0.18, 0.22, 0.44],
      "payload": {
        "colony": "Pluto"
      }
    }
  ]
}
PUT collections/star_charts/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.05, 0.61, 0.76, 0.74],
      "payload": {
        "colony": "Mars"
      }
    },
    {
      "id": 2,
      "vector": [0.19, 0.81, 0.75, 0.11],
      "payload": {
        "colony": "Jupiter"
      }
    },
    {
      "id": 3,
      "vector": [0.36, 0.55, 0.47, 0.94],
      "payload": {
        "colony": "Venus"
      }
    },
    {
      "id": 4,
      "vector": [0.18, 0.01, 0.85, 0.80],
      "payload": {
        "colony": "Moon"
      }
    },
    {
      "id": 5,
      "vector": [0.24, 0.18, 0.22, 0.44],
      "payload": {
        "colony": "Pluto"
      }
    }
  ]
}
Step 3: Run a search query
Now, let’s search for the three nearest colonies to a specific vector representing a spatial location. This query will return the colonies along with their payload information.

Run the query below to find the nearest colonies:

POST collections/star_charts/points/search
{
  "vector": [0.2, 0.1, 0.9, 0.7],
  "limit": 3,
  "with_payload": true
}
POST collections/star_charts/points/search
{
  "vector": [0.2, 0.1, 0.9, 0.7],
  "limit": 3,
  "with_payload": true
}
Conclusion
Congratulations! 🎉 You’ve just completed a vector search across galactic coordinates! You've successfully added spatial data into a collection and performed searches to find the nearest locations based on their vector representation.

Next steps
In the next section, you’ll explore creating complex filter conditions to refine your searches further for interstellar exploration!



#Load Data into a Collection from a Remote Snapshot
In this tutorial, we will guide you through loading data into a Qdrant collection from a remote snapshot.

Step 1: Import a snapshot to a collection
To start, create the collection midjourney and load vector data into it. The collection will take on the parameters of the snapshot, with vector size of 512, and similarity measured using the Cosine distance.

PUT /collections/midjourney/snapshots/recover
{
  "location": "http://snapshots.qdrant.io/midlib.snapshot"
}
PUT /collections/midjourney/snapshots/recover
{
  "location": "http://snapshots.qdrant.io/midlib.snapshot"
}
Wait a few moments while the vectors from the snapshot are added to the midjourney collection.

Step 2: Verify the data upload
After the data has been imported, it's important to verify that it has been successfully uploaded. You can do this by checking the number of vectors (or points) in the collection.

Run the following request to get the vector count:

POST /collections/midjourney/points/count
POST /collections/midjourney/points/count
The collection should contain 5,417 data points.

Step 4: Open the collection UI
You can also inspect your collection to review the uploaded data.


Basic Filtering - Clauses and Conditions
Step 1: Create a Collection
First, create a collection called terraforming. Each point will have vectors of size 4, and the distance metric is set to Dot:

PUT collections/terraforming
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
PUT collections/terraforming
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
Step 2: Add Points with Vectors and Payloads
Now, add points to the collection. Each point includes an id, vector and a payload with various attributes like land type, color, life presence, and humidity:

PUT collections/terraforming/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, 0.4],
      "payload": {"land": "forest", "color": "green", "life": true, "humidity": 40}
    },
    {
      "id": 2,
      "vector": [0.2, 0.3, 0.4, 0.5],
      "payload": {"land": "lake", "color": "blue", "life": true, "humidity": 100}
    },
    {
      "id": 3,
      "vector": [0.3, 0.4, 0.5, 0.6],
      "payload": {"land": "steppe", "color": "green", "life": false, "humidity": 25}
    },
    {
      "id": 4,
      "vector": [0.4, 0.5, 0.6, 0.7],
      "payload": {"land": "desert", "color": "red", "life": false, "humidity": 5}
    },
    {
      "id": 5,
      "vector": [0.5, 0.6, 0.7, 0.8],
      "payload": {"land": "marsh", "color": "black", "life": true, "humidity": 90}
    },
    {
      "id": 6,
      "vector": [0.6, 0.7, 0.8, 0.9],
      "payload": {"land": "cavern", "color": "black", "life": false, "humidity": 15}
    }
  ]
}
PUT collections/terraforming/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, 0.4],
      "payload": {"land": "forest", "color": "green", "life": true, "humidity": 40}
    },
    {
      "id": 2,
      "vector": [0.2, 0.3, 0.4, 0.5],
      "payload": {"land": "lake", "color": "blue", "life": true, "humidity": 100}
    },
    {
      "id": 3,
      "vector": [0.3, 0.4, 0.5, 0.6],
      "payload": {"land": "steppe", "color": "green", "life": false, "humidity": 25}
    },
    {
      "id": 4,
      "vector": [0.4, 0.5, 0.6, 0.7],
      "payload": {"land": "desert", "color": "red", "life": false, "humidity": 5}
    },
    {
      "id": 5,
      "vector": [0.5, 0.6, 0.7, 0.8],
      "payload": {"land": "marsh", "color": "black", "life": true, "humidity": 90}
    },
    {
      "id": 6,
      "vector": [0.6, 0.7, 0.8, 0.9],
      "payload": {"land": "cavern", "color": "black", "life": false, "humidity": 15}
    }
  ]
}
Step 3: Index the fields before filtering
Note: You should always index a field before filtering. If you use filtering before you create an index, Qdrant will search through the entire dataset in an unstructured way. Your search performance will be very slow.

PUT /collections/terraforming/index
{
    "field_name": "life",
    "field_schema": "bool"
}
PUT /collections/terraforming/index
{
    "field_name": "life",
    "field_schema": "bool"
}
PUT /collections/terraforming/index
{
    "field_name": "color",
    "field_schema": "keyword"
}
PUT /collections/terraforming/index
{
    "field_name": "color",
    "field_schema": "keyword"
}
PUT /collections/terraforming/index
{
    "field_name": "humidity",
    "field_schema": {
       "type": "integer",
        "range": true
    }
}
PUT /collections/terraforming/index
{
    "field_name": "humidity",
    "field_schema": {
       "type": "integer",
        "range": true
    }
}
Step 4: Filtering examples
Filter by exact match
Finally, this query retrieves points where the color is "black", using a straightforward match condition:

POST collections/terraforming/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "color",
        "match": {
          "value": "black"
        }
      }
    ]
  },
  "limit": 3,
  "with_payload": true
}
POST collections/terraforming/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "color",
        "match": {
          "value": "black"
        }
      }
    ]
  },
  "limit": 3,
  "with_payload": true
}
Combined filter by must clause
In this example, the query returns points where life is true and color is "green". These must conditions both need to be met for a point to be returned.

POST collections/terraforming/points/scroll
{
  "filter": {
    "must": [
      { "key": "life", "match": { "value": true } },
      { "key": "color", "match": { "value": "green" } }
    ]
  },
  "limit": 3,
  "with_payload": true
}
POST collections/terraforming/points/scroll
{
  "filter": {
    "must": [
      { "key": "life", "match": { "value": true } },
      { "key": "color", "match": { "value": "green" } }
    ]
  },
  "limit": 3,
  "with_payload": true
}
Filter by should clause
Here, you are filtering for points where life is false and color is "black". These conditions act as should clauses, meaning points meeting either or both criteria will be returned:

POST collections/terraforming/points/scroll
{
  "filter": {
    "should": [
      {
        "key": "life",
        "match": { "value": false }
      }, {
        "key": "color",
        "match": { "value": "black" }
      }
    ]
  }
}
POST collections/terraforming/points/scroll
{
  "filter": {
    "should": [
      {
        "key": "life",
        "match": { "value": false }
      }, {
        "key": "color",
        "match": { "value": "black" }
      }
    ]
  }
}

Filter by must_not clause
This query filters out any points where life is false. Points matching this condition are excluded from the results.

POST collections/terraforming/points/scroll
{
  "filter": {
    "must_not": [
      {
       "key": "life",
       "match": { "value": false }
      }
    ]
  },
  "limit": 3,
  "with_payload": true
}
POST collections/terraforming/points/scroll
{
  "filter": {
    "must_not": [
      {
       "key": "life",
       "match": { "value": false }
      }
    ]
  },
  "limit": 3,
  "with_payload": true
}
Filter by range condition
This query filters points based on a range of humidity. Here, the humidity value must be exactly 40:

POST collections/terraforming/points/scroll
{
  "filter": {
    "must": [
      {
       "key": "humidity",
       "range": {
         "gte": 40,
         "lte": 40
       }
      }
    ]
  },
  "limit": 3,
  "with_payload": true
}
POST collections/terraforming/points/scroll
{
  "filter": {
    "must": [
      {
       "key": "humidity",
       "range": {
         "gte": 40,
         "lte": 40
       }
      }
    ]
  },
  "limit": 3,
  "with_payload": true
}


#Advanced Filtering - Nested Filters
Step 1: Create a Collection
Start by creating a collection named dinosaurs with a vector size of 4 and the distance metric set to Dot:

PUT collections/dinosaurs
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
PUT collections/dinosaurs
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
Step 2: Add Vectors with Payloads
You can now add points to the collection. Each point contains an id, vector and a payload with additional information such as the dinosaur species and diet preferences. For example:

PUT collections/dinosaurs/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, 0.4],
      "payload": {
        "dinosaur": "t-rex",
        "diet": [
          { "food": "leaves", "likes": false },
          { "food": "meat", "likes": true }
        ]
      }
    },
    {
      "id": 2,
      "vector": [0.2, 0.3, 0.4, 0.5],
      "payload": {
        "dinosaur": "diplodocus",
        "diet": [
          { "food": "leaves", "likes": true },
          { "food": "meat", "likes": false }
        ]
      }
    }
  ]
}
PUT collections/dinosaurs/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, 0.4],
      "payload": {
        "dinosaur": "t-rex",
        "diet": [
          { "food": "leaves", "likes": false },
          { "food": "meat", "likes": true }
        ]
      }
    },
    {
      "id": 2,
      "vector": [0.2, 0.3, 0.4, 0.5],
      "payload": {
        "dinosaur": "diplodocus",
        "diet": [
          { "food": "leaves", "likes": true },
          { "food": "meat", "likes": false }
        ]
      }
    }
  ]
}
Step 3: Index the fields before filtering
Note: You should always index a field before filtering. If you use filtering before you create an index, Qdrant will search through the entire dataset in an unstructured way. Your search performance will be very slow.

PUT /collections/dinosaurs/index
{
    "field_name": "diet[].food",
    "field_schema": "keyword"
}
PUT /collections/dinosaurs/index
{
    "field_name": "diet[].food",
    "field_schema": "keyword"
}
PUT /collections/dinosaurs/index
{
    "field_name": "diet[].likes",
    "field_schema": "bool"
}
PUT /collections/dinosaurs/index
{
    "field_name": "diet[].likes",
    "field_schema": "bool"
}
Step 4: Basic Filtering with match
You can filter points by specific payload values. For instance, the query below matches points where:

The diet[].food contains "meat".
The diet[].likes is set to true.
Both points match these conditions, as:

The “t-rex” eats meat and likes it.
The “diplodocus” eats meat but doesn't like it.
POST /collections/dinosaurs/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "diet[].food",
        "match": {
          "value": "meat"
        }
      },
      {
        "key": "diet[].likes",
        "match": {
          "value": true
        }
      }
    ]
  }
}
POST /collections/dinosaurs/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "diet[].food",
        "match": {
          "value": "meat"
        }
      },
      {
        "key": "diet[].likes",
        "match": {
          "value": true
        }
      }
    ]
  }
}
However, if you want to retrieve only the points where both conditions are true for the same element within the array (e.g., the "t-rex" with ID 1), you'll need to use a nested filter.

Step 5: Advanced Filtering with Nested Object Filters
To apply the filter at the array element level, you use the nested filter condition. This ensures that the food and likes values are evaluated together within each array element:

POST /collections/dinosaurs/points/scroll
{
  "filter": {
    "must": [
      {
        "nested": {
          "key": "diet",
          "filter": {
            "must": [
              {
                "key": "food",
                "match": {
                  "value": "meat"
                }
              },
              {
                "key": "likes",
                "match": {
                  "value": true
                }
              }
            ]
          }
        }
      }
    ]
  }
}
POST /collections/dinosaurs/points/scroll
{
  "filter": {
    "must": [
      {
        "nested": {
          "key": "diet",
          "filter": {
            "must": [
              {
                "key": "food",
                "match": {
                  "value": "meat"
                }
              },
              {
                "key": "likes",
                "match": {
                  "value": true
                }
              }
            ]
          }
        }
      }
    ]
  }
}
With this filter, only the "t-rex" (ID 1) is returned, because its array element satisfies both conditions.

Explanation
Nested filters treat each array element as a separate object, applying the filter independently to each element. The parent document (in this case, the dinosaur point) matches the filter if any one array element meets all conditions.

Step 6: Combining has_id with Nested Filters
Note that has_id cannot be used inside a nested filter. If you need to filter by ID as well, include the has_id condition as a separate clause, like this:

You won't get a different answer. You can see that this filter matches the "t-rex" (ID 1) by combining the nested diet filter with an explicit ID match.

POST /collections/dinosaurs/points/scroll
{
  "filter": {
    "must": [
      {
        "nested": {
          "key": "diet",
          "filter": {
            "must": [
              {
                "key": "food",
                "match": {
                  "value": "meat"
                }
              },
              {
                "key": "likes",
                "match": {
                  "value": true
                }
              }
            ]
          }
        }
      },
      {
        "has_id": [1]
      }
    ]
  }
}
POST /collections/dinosaurs/points/scroll
{
  "filter": {
    "must": [
      {
        "nested": {
          "key": "diet",
          "filter": {
            "must": [
              {
                "key": "food",
                "match": {
                  "value": "meat"
                }
              },
              {
                "key": "likes",
                "match": {
                  "value": true
                }
              }
            ]
          }
        }
      },
      {
        "has_id": [1]
      }
    ]
  }
}

#Full Text Filtering
Here's a step-by-step tutorial on Full Text Filtering in Qdrant using a collection of planetary data with description fields:

Step 1: Create a collection
We first create a collection named star_charts with vectors of size 4 and dot product distance for similarity.

PUT /collections/star_charts
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
PUT /collections/star_charts
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
Step 2: Add data with descriptions in payload
Next, we add data to the collection. Each entry includes an id, vector and a payload containing details about various celestial bodies, such as colony information, whether the body supports life and a description.

PUT collections/star_charts/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.05, 0.61, 0.76, 0.74],
      "payload": {
        "colony": "Mars",
        "supports_life": true,
        "description": "The red planet, Mars, has a cold desert climate and may have once had conditions suitable for life."
      }
    },
    {
      "id": 2,
      "vector": [0.19, 0.81, 0.75, 0.11],
      "payload": {
        "colony": "Jupiter",
        "supports_life": false,
        "description": "Jupiter is the largest planet in the solar system, known for its Great Red Spot and hostile gas environment."
      }
    },
    {
      "id": 3,
      "vector": [0.36, 0.55, 0.47, 0.94],
      "payload": {
        "colony": "Venus",
        "supports_life": false,
        "description": "Venus, Earth’s twin in size, has an extremely thick atmosphere and surface temperatures hot enough to melt lead."
      }
    },
    {
      "id": 4,
      "vector": [0.18, 0.01, 0.85, 0.80],
      "payload": {
        "colony": "Moon",
        "supports_life": true,
        "description": "Earth’s Moon, long visited by astronauts, is a barren, airless world but could host colonies in its underground caves."
      }
    },
    {
      "id": 5,
      "vector": [0.24, 0.18, 0.22, 0.44],
      "payload": {
        "colony": "Pluto",
        "supports_life": false,
        "description": "Once considered the ninth planet, Pluto is a small icy world at the edge of the solar system."
      }
    }
  ]
}
PUT collections/star_charts/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.05, 0.61, 0.76, 0.74],
      "payload": {
        "colony": "Mars",
        "supports_life": true,
        "description": "The red planet, Mars, has a cold desert climate and may have once had conditions suitable for life."
      }
    },
    {
      "id": 2,
      "vector": [0.19, 0.81, 0.75, 0.11],
      "payload": {
        "colony": "Jupiter",
        "supports_life": false,
        "description": "Jupiter is the largest planet in the solar system, known for its Great Red Spot and hostile gas environment."
      }
    },
    {
      "id": 3,
      "vector": [0.36, 0.55, 0.47, 0.94],
      "payload": {
        "colony": "Venus",
        "supports_life": false,
        "description": "Venus, Earth’s twin in size, has an extremely thick atmosphere and surface temperatures hot enough to melt lead."
      }
    },
    {
      "id": 4,
      "vector": [0.18, 0.01, 0.85, 0.80],
      "payload": {
        "colony": "Moon",
        "supports_life": true,
        "description": "Earth’s Moon, long visited by astronauts, is a barren, airless world but could host colonies in its underground caves."
      }
    },
    {
      "id": 5,
      "vector": [0.24, 0.18, 0.22, 0.44],
      "payload": {
        "colony": "Pluto",
        "supports_life": false,
        "description": "Once considered the ninth planet, Pluto is a small icy world at the edge of the solar system."
      }
    }
  ]
}
Step 3: Try filtering with exact phrase (substring match)
Now, let's try to filter the descriptions to find entries that contain the exact phrase "host colonies." Qdrant supports text filtering by default using exact matches, but note that this will not tokenize the text.

POST /collections/star_charts/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "description",
        "match": {
          "text": "host colonies"
        }
      }
    ]
  },
  "limit": 2,
  "with_payload": true
}
POST /collections/star_charts/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "description",
        "match": {
          "text": "host colonies"
        }
      }
    ]
  },
  "limit": 2,
  "with_payload": true
}
You’ll notice this filter works, but if you change the phrase slightly, it won’t return results, since substring matching in unindexed text isn’t flexible enough for variations.

Step 4: Index the description field
To make filtering more powerful and flexible, we’ll index the description field. This will tokenize the text, allowing for more complex queries such as filtering for phrases like "cave colonies." We use a word tokenizer, and only tokens that are between 5 and 20 characters will be indexed.

Note: You should always index a field before filtering. If you use filtering before you create an index (like in Step 3), Qdrant will search through the entire dataset in an unstructured way. Your search performance will be very slow.

PUT /collections/star_charts/index
{
    "field_name": "description",
    "field_schema": {
        "type": "text",
        "tokenizer": "word",
        "lowercase": true
    }
}
PUT /collections/star_charts/index
{
    "field_name": "description",
    "field_schema": {
        "type": "text",
        "tokenizer": "word",
        "lowercase": true
    }
}
Step 5: Try the filter again
After indexing, you can now run the filter again, but this time not searching for a phrase. Now you will filter for all tokens "cave" AND "colonies" from the descriptions.

POST /collections/star_charts/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "description",
        "match": {
          "text": "cave colonies"
        }
      }
    ]
  },
  "limit": 2,
  "with_payload": true
}
POST /collections/star_charts/points/scroll
{
  "filter": {
    "must": [
      {
        "key": "description",
        "match": {
          "text": "cave colonies"
        }
      }
    ]
  },
  "limit": 2,
  "with_payload": true
}
Summary
Phrase search requires tokens to come in and exact sequence, and by indexing all words we are ignoring the sequence completely and filtering for relevant keywords.

#Search with ColBERT Multivectors
In Qdrant, multivectors allow you to store and search multiple vectors for each point in your collection. Additionally, you can store payloads, which are key-value pairs containing metadata about each point. This tutorial will show you how to create a collection, insert points with multivectors and payloads, and perform a search.

Step 1: Create a collection with multivectors
To use multivectors, you need to configure your collection to store multiple vectors per point. The collection’s configuration specifies the vector size, distance metric, and multivector settings, such as the comparator function.

Run the following request to create a collection with multivectors:

PUT collections/multivector_collection
{
  "vectors": {
    "size": 4,
    "distance": "Dot",
    "multivector_config": {
      "comparator": "max_sim"
    }
  }
}
PUT collections/multivector_collection
{
  "vectors": {
    "size": 4,
    "distance": "Dot",
    "multivector_config": {
      "comparator": "max_sim"
    }
  }
}
Step 2: Insert points with multivectors and payloads
Now that the collection is set up, you can insert points where each point contains multiple vectors and a payload. Payloads store additional metadata, such as the planet name and its type.

Run the following request to insert points with multivectors and payloads:

PUT collections/multivector_collection/points
{
  "points": [
    {
      "id": 1,
      "vector": [
        [-0.013,  0.020, -0.007, -0.111],
        [-0.030, -0.015,  0.021,  0.072],
        [0.041,  -0.004, 0.032,  0.062]
      ],
      "payload": {
        "name": "Mars",
        "type": "terrestrial"
      }
    },
    {
      "id": 2,
      "vector": [
        [0.011,  -0.050,  0.007,  0.101],
        [0.031,  0.014,  -0.032,  0.012]
      ],
      "payload": {
        "name": "Jupiter",
        "type": "gas giant"
      }
    },
    {
      "id": 3,
      "vector": [
        [0.041,  0.034,  -0.012, -0.022],
        [0.040,  -0.095,  0.021,  0.032],
        [-0.030,  0.025,  0.011,  0.082],
        [0.021,  -0.044,  0.032, -0.032]
      ],
      "payload": {
        "name": "Venus",
        "type": "terrestrial"
      }
    },
    {
      "id": 4,
      "vector": [
        [-0.015,  0.020,  0.045,  -0.131],
        [0.041,   -0.024, -0.032,  0.072]
      ],
      "payload": {
        "name": "Neptune",
        "type": "ice giant"
      }
    }
  ]
}
PUT collections/multivector_collection/points
{
  "points": [
    {
      "id": 1,
      "vector": [
        [-0.013,  0.020, -0.007, -0.111],
        [-0.030, -0.015,  0.021,  0.072],
        [0.041,  -0.004, 0.032,  0.062]
      ],
      "payload": {
        "name": "Mars",
        "type": "terrestrial"
      }
    },
    {
      "id": 2,
      "vector": [
        [0.011,  -0.050,  0.007,  0.101],
        [0.031,  0.014,  -0.032,  0.012]
      ],
      "payload": {
        "name": "Jupiter",
        "type": "gas giant"
      }
    },
    {
      "id": 3,
      "vector": [
        [0.041,  0.034,  -0.012, -0.022],
        [0.040,  -0.095,  0.021,  0.032],
        [-0.030,  0.025,  0.011,  0.082],
        [0.021,  -0.044,  0.032, -0.032]
      ],
      "payload": {
        "name": "Venus",
        "type": "terrestrial"
      }
    },
    {
      "id": 4,
      "vector": [
        [-0.015,  0.020,  0.045,  -0.131],
        [0.041,   -0.024, -0.032,  0.072]
      ],
      "payload": {
        "name": "Neptune",
        "type": "ice giant"
      }
    }
  ]
}
Step 3: Query the collection
To perform a search with multivectors, you can pass multiple query vectors. Qdrant will compare the query vectors against the multivectors and return the most similar results based on the comparator defined for the collection (max_sim). You can also request the payloads to be returned along with the search results.

Run the following request to search with multivectors and retrieve the payloads:

POST collections/multivector_collection/points/query
{
  "query": [
    [-0.015,  0.020,  0.045,  -0.131],
    [0.030,   -0.005, 0.001,   0.022],
    [0.041,   -0.024, -0.032,  0.072]
  ],
  "with_payload": true
}
POST collections/multivector_collection/points/query
{
  "query": [
    [-0.015,  0.020,  0.045,  -0.131],
    [0.030,   -0.005, 0.001,   0.022],
    [0.041,   -0.024, -0.032,  0.072]
  ],
  "with_payload": true
}

#Sparse Vector Search
In this tutorial, you'll learn how to create a collection with sparse vectors in Qdrant, insert points with sparse vectors, and query them based on specific indices and values. Sparse vectors allow you to efficiently store and search data with only certain dimensions being non-zero, which is particularly useful in applications like text embeddings or handling sparse data.

Step 1: Create a collection with sparse vectors
The first step is to create a collection that can handle sparse vectors. Unlike dense vectors that represent full feature spaces, sparse vectors only store non-zero values in select positions, making them more efficient. We’ll create a collection called sparse_charts where each point will have sparse vectors to represent keywords or other features.

Run the following request to create the collection:

PUT /collections/sparse_charts
{
    "sparse_vectors": {
        "keywords": {}
    }
}
PUT /collections/sparse_charts
{
    "sparse_vectors": {
        "keywords": {}
    }
}
Explanation:
sparse_vectors: Defines that the collection supports sparse vectors, in this case, indexed by "keywords." This can represent keyword-based features where only certain indices (positions) have non-zero values.
Step 2: Insert data points with sparse vectors
Once the collection is ready, you can insert points with sparse vectors. Each point will include:

indices: The positions of non-zero values in the vector space.
values: The corresponding values at those positions, representing the importance or weight of each keyword or feature.
Run the following request to insert the points:

PUT /collections/sparse_charts/points
{
    "points": [
        {
            "id": 1,
            "vector": {
                "keywords": {
                    "indices": [1, 42],
                    "values": [0.22, 0.8]
                }
            }
        },
        {
            "id": 2,
            "vector": {
                "keywords": {
                    "indices": [2, 35],
                    "values": [0.15, 0.65]
                }
            }
        },
        {
            "id": 3,
            "vector": {
                "keywords": {
                    "indices": [10, 42],
                    "values": [0.3, 0.5]
                }
            }
        },
        {
            "id": 4,
            "vector": {
                "keywords": {
                    "indices": [0, 3],
                    "values": [0.4, 0.3]
                }
            }
        },
        {
            "id": 5,
            "vector": {
                "keywords": {
                    "indices": [2, 4],
                    "values": [0.9, 0.8]
                }
            }
        }
    ]
}
PUT /collections/sparse_charts/points
{
    "points": [
        {
            "id": 1,
            "vector": {
                "keywords": {
                    "indices": [1, 42],
                    "values": [0.22, 0.8]
                }
            }
        },
        {
            "id": 2,
            "vector": {
                "keywords": {
                    "indices": [2, 35],
                    "values": [0.15, 0.65]
                }
            }
        },
        {
            "id": 3,
            "vector": {
                "keywords": {
                    "indices": [10, 42],
                    "values": [0.3, 0.5]
                }
            }
        },
        {
            "id": 4,
            "vector": {
                "keywords": {
                    "indices": [0, 3],
                    "values": [0.4, 0.3]
                }
            }
        },
        {
            "id": 5,
            "vector": {
                "keywords": {
                    "indices": [2, 4],
                    "values": [0.9, 0.8]
                }
            }
        }
    ]
}
Explanation:
Each point is represented by its sparse vector, defined with specific keyword indices and values.
For example, Point 1 has sparse vector values of 0.22 and 0.8 at positions 1 and 42, respectively. These could represent the relative importance of keywords associated with those positions.
Run a query with specific indices and values
This query searches for points that have non-zero values at the positions [1, 42] and specific values [0.22, 0.8]. This is a targeted query and expects a close match to these indices and values.

POST /collections/sparse_charts/points/query
{
    "query": {
        "indices": [1, 42],
        "values": [0.22, 0.8]
    },
    "using": "keywords"
}
POST /collections/sparse_charts/points/query
{
    "query": {
        "indices": [1, 42],
        "values": [0.22, 0.8]
    },
    "using": "keywords"
}
Expected result: Point 1 would be the best match since its sparse vector includes these indices that maximize the measure of similarity. In this case, this is the dot product calculation.

Breaking down the scoring mechanism
This query searches for points with non-zero values at positions [0, 2, 4] and values [0.4, 0.9, 0.8]. It’s a broader search that might return multiple matches with overlapping indices and similar values.

POST /collections/sparse_charts/points/query
{
    "query": {
        "indices": [0, 2, 4],
        "values": [0.4, 0.9, 0.8]
    },
    "using": "keywords"
}
POST /collections/sparse_charts/points/query
{
    "query": {
        "indices": [0, 2, 4],
        "values": [0.4, 0.9, 0.8]
    },
    "using": "keywords"
}
How we got this result:
Let's assume the sparse vectors of Point 4 and Point 5 are as follows:

Point 4: [0.4, 0, 0, 0, 0] (Matches query at index 0 with value 0.4)
Point 5: [0, 0, 0.9, 0, 0.8] (Matches query at indices 2 and 4 with values 0.9 and 0.8)
The dot product would look something like:

Dot product for Point 4:

Query: [0.4, 0, 0.9, 0, 0.8]
Point 4: [0.4, 0, 0, 0, 0]
Dot product: ( 0.4 * 0.4 = 0.16 )
Dot product for Point 5:

Query: [0.4, 0, 0.9, 0, 0.8]
Point 5: [0, 0, 0.9, 0, 0.8]
Dot product: ( 0.9 * 0.9 + 0.8 * 0.8 = 0.81 + 0.64 = 1.45 )
Since Point 5 has a higher dot product score, it would be considered a better match than Point 4.

#Separate User Data in Multitenant Setups
In this tutorial, we will cover how to implement multitenancy in Qdrant. Multitenancy allows you to host multiple tenants or clients within a single instance of Qdrant, ensuring data isolation and access control between tenants. This feature is essential for use cases where you need to serve different clients while maintaining separation of their data.

Step 1: Create a collection
Imagine you are running a recommendation service where different departments (tenants) store their data in Qdrant. By using payload-based multitenancy, you can keep all tenants’ data in a single collection but filter the data based on a unique tenant identifier.

Run the following request to create a shared collection for all tenants:

PUT collections/central_library
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
PUT collections/central_library
{
  "vectors": {
    "size": 4,
    "distance": "Dot"
  }
}
Step 2: Build a tenant index
Qdrant supports efficient indexing based on the tenant's identifier to optimize multitenant searches. By enabling tenant indexing, you can structure data on disk for faster tenant-specific searches, improving performance and reducing disk reads.

Run the following request to enable indexing for the tenant identifier (group_id):

PUT /collections/central_library/index
{
    "field_name": "group_id",
    "field_schema": {
        "type": "keyword",
        "is_tenant": true
    }
}
PUT /collections/central_library/index
{
    "field_name": "group_id",
    "field_schema": {
        "type": "keyword",
        "is_tenant": true
    }
}
Step 3: Load vectors for tenants
Next, you will load data into the shared collection. Each data point is tagged with a tenant-specific identifier in the payload. This identifier (group_id) ensures that tenants' data remains isolated even when stored in the same collection.

Run the following request to insert data points:

PUT /collections/central_library/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, 0.4],    
      "payload": {
        "group_id": "user_1",
        "station": "Communications",
        "message_log": "Contact with colony headquarters."
      }
    },
    {
      "id": 2,
      "vector": [0.5, 0.6, 0.7, 0.8],
      "payload": {
        "group_id": "user_2",
        "station": "Security",
        "message_log": "Monitor intruder alert system."
      }
    },
    {
      "id": 3,
      "vector": [0.9, 1.0, 1.1, 1.2],
      "payload": {
        "group_id": "user_3",
        "station": "Engineering",
        "message_log": "Repair warp core malfunction."
      }
    }
  ]
}
PUT /collections/central_library/points
{
  "points": [
    {
      "id": 1,
      "vector": [0.1, 0.2, 0.3, 0.4],    
      "payload": {
        "group_id": "user_1",
        "station": "Communications",
        "message_log": "Contact with colony headquarters."
      }
    },
    {
      "id": 2,
      "vector": [0.5, 0.6, 0.7, 0.8],
      "payload": {
        "group_id": "user_2",
        "station": "Security",
        "message_log": "Monitor intruder alert system."
      }
    },
    {
      "id": 3,
      "vector": [0.9, 1.0, 1.1, 1.2],
      "payload": {
        "group_id": "user_3",
        "station": "Engineering",
        "message_log": "Repair warp core malfunction."
      }
    }
  ]
}
Step 4: Perform a filtered query
When querying the shared collection, use the group_id payload field to ensure tenants can only access their own data. The filter in this query ensures that only points belonging to the specified group_id are returned.

Run the following request to search for data specific to user_1:

POST /collections/central_library/points/query
{
    "query": [0.2, 0.1, 0.9, 0.7],
    "filter": {
        "must": [
            {
                "key": "group_id",
                "match": {
                    "value": "user_1"
                }
            }
        ]
    },
    "limit": 2,
    "with_payload": true
}
POST /collections/central_library/points/query
{
    "query": [0.2, 0.1, 0.9, 0.7],
    "filter": {
        "must": [
            {
                "key": "group_id",
                "match": {
                    "value": "user_1"
                }
            }
        ]
    },
    "limit": 2,
    "with_payload": true
}
Step 5: Add more data
If needed, you can add more data points for multiple tenants. This example shows how to expand the collection with new points tagged with different group_id values:

Add more data
PUT /collections/central_library/points
{
  "points": [
    {
      "id": 4,
      "vector": [0.89, 0.95, 1.03, 0.99],
      "payload": {
        "group_id": "user_4",
        "station": "Medical",
        "message_log": "Prepare medical supplies."
      }
    },
    {
      "id": 5,
      "vector": [0.82, 0.87, 0.83, 0.88],
      "payload": {
        "group_id": "user_5",
        "station": "Operations",
        "message_log": "Schedule maintenance for the day."
      }
    },
    {
      "id": 6,
      "vector": [0.91, 1.05, 0.96, 0.90],
      "payload": {
        "group_id": "user_1",
        "station": "Communications",
        "message_log": "Dispatch signal to rescue team."
      }
    },
    {
      "id": 7,
      "vector": [0.78, 0.86, 0.84, 0.81],
      "payload": {
        "group_id": "user_2",
        "station": "Security",
        "message_log": "Check perimeter for breaches."
      }
    },
    {
      "id": 8,
      "vector": [1.04, 0.97, 1.01, 0.93],
      "payload": {
        "group_id": "user_3",
        "station": "Engineering",
        "message_log": "Run diagnostics on the shield generator."
      }
    }
  ]
}
PUT /collections/central_library/points
{
  "points": [
    {
      "id": 4,
      "vector": [0.89, 0.95, 1.03, 0.99],
      "payload": {
        "group_id": "user_4",
        "station": "Medical",
        "message_log": "Prepare medical supplies."
      }
    },
    {
      "id": 5,
      "vector": [0.82, 0.87, 0.83, 0.88],
      "payload": {
        "group_id": "user_5",
        "station": "Operations",
        "message_log": "Schedule maintenance for the day."
      }
    },
    {
      "id": 6,
      "vector": [0.91, 1.05, 0.96, 0.90],
      "payload": {
        "group_id": "user_1",
        "station": "Communications",
        "message_log": "Dispatch signal to rescue team."
      }
    },
    {
      "id": 7,
      "vector": [0.78, 0.86, 0.84, 0.81],
      "payload": {
        "group_id": "user_2",
        "station": "Security",
        "message_log": "Check perimeter for breaches."
      }
    },
    {
      "id": 8,
      "vector": [1.04, 0.97, 1.01, 0.93],
      "payload": {
        "group_id": "user_3",
        "station": "Engineering",
        "message_log": "Run diagnostics on the shield generator."
      }
    }
  ]
}
Step 6: Group query results
You can group query results by specific fields, such as station, to get an overview of each tenant's data. This query groups results by station and limits the number of groups and the number of points per group.

Run the following request to group the results by station:

POST /collections/central_library/points/query/groups
{
    "query": [0.01, 0.45, 0.6, 0.88],
    "group_by": "station",  
    "limit": 5,  
    "group_size": 5,
    "with_payload": true  
}
POST /collections/central_library/points/query/groups
{
    "query": [0.01, 0.45, 0.6, 0.88],
    "group_by": "station",  
    "limit": 5,  
    "group_size": 5,
    "with_payload": true  
}
