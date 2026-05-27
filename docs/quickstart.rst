Quick Start
===========

Run all benchmark suites:

.. code-block:: bash

   agentbench run http://localhost:8080

Run specific suites:

.. code-block:: bash

   agentbench run http://localhost:8080 --suites prompt_injection,ssrf

Compare results:

.. code-block:: bash

   agentbench compare baseline.json target.json

Generate a leaderboard:

.. code-block:: bash

   agentbench leaderboard result1.json result2.json result3.json
